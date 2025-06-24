from typing import Dict, List
import torch
import numpy as np
from transformers.models.whisper import WhisperProcessor, WhisperForConditionalGeneration
from pydub import AudioSegment
import os
import math
# import openai
import re
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import aiofiles
from openai import AsyncOpenAI

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def split_sentences_with_overlap(text):
    chunk_size = 7
    stride = 2
    sentences = re.split(r'(?<=[.!?])["”’]?[\s\n]+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    chunks = []
    n = len(sentences)
    start = 0
    while start < n:
        end = min(start + chunk_size, n)
        chunk = sentences[start:end]
        chunks.append(' '.join(chunk))
        if end == n:
            break
        start += chunk_size - stride
    return chunks

def split_audio_to_chunks(file_path: str, chunk_length_sec: int = 150, overlap_sec: int = 4) -> List[str]:
    """
    오디오 파일을 chunk_length_sec(초) 단위로 분할, overlap_sec(초)만큼 겹치게 분할
    각 청크는 임시 파일로 저장되고, 파일 경로 리스트를 반환
    """
    audio = AudioSegment.from_file(file_path)
    audio = audio.set_frame_rate(16000).set_channels(1)
    total_length_ms = len(audio)
    chunk_length_ms = chunk_length_sec * 1000
    overlap_ms = overlap_sec * 1000
    chunk_paths = []
    start = 0
    idx = 0
    while start < total_length_ms:
        end = min(start + chunk_length_ms, total_length_ms)
        chunk = audio[start:end]
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_chunk_{idx}.wav") as tmp:
            chunk.export(tmp.name, format="wav")
            chunk_paths.append(tmp.name)
        if end == total_length_ms:
            break
        start += chunk_length_ms - overlap_ms
        idx += 1
    return chunk_paths




async def transcribe_chunk(chunk_path: str) -> str:
    """
    Whisper API로 청크 파일을 변환하는 함수 (AsyncOpenAI 사용)
    """
    try:
        async with aiofiles.open(chunk_path, "rb") as audio_file:
            audio_data = await audio_file.read()

        # Whisper에 오디오 파일 전달 (주의: file은 바이너리 객체로 전달해야 함)
        transcript = await openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=(os.path.basename(chunk_path), audio_data),
            response_format="text"
        )
        return str(transcript).strip()

    except Exception as e:
        return f"[ERROR] {e}"


def merge_chunks_texts(chunk_texts: List[str], overlap_sec: int = 4) -> str:
    """
    청크별 텍스트를 순서대로 병합, 겹치는 부분(문장 단위) 제거
    """
    merged = []
    prev = ""
    for text in chunk_texts:
        # 문장 단위로 분할
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        if prev:
            # 이전 청크 마지막 1~2문장과 현재 청크 첫 1~2문장 비교해서 겹치면 제거
            prev_last = prev[-2:] if len(prev) >= 2 else prev
            curr_first = sentences[:2] if len(sentences) >= 2 else sentences
            overlap = 0
            for i in range(min(len(prev_last), len(curr_first)), 0, -1):
                if prev_last[-i:] == curr_first[:i]:
                    overlap = i
                    break
            sentences = sentences[overlap:]
        merged.extend(sentences)
        prev = sentences
    return " ".join(merged).strip()


async def gpt_refine_text(raw_text: str) -> str:
    """
    Whisper API로 추출된 텍스트를 GPT API로 자연스럽게 다듬는 함수
    """
    prompt = (
        "다음은 Whisper API로 변환된 한국어 회의 내용입니다.  "
        "발음 오류나 어색한 표현, 잘못된 단어가 있을 수 있습니다.  "
        "이 텍스트를 다음 조건에 맞게 자연스럽게 다듬어주세요:\n"
        "1. 문맥에 맞는 단어로 고쳐주세요 (예: '바라자' → '발화자')\n"
        "2. 문장 부호(. ? !)를 적절히 추가해주세요\n"
        "3. 전체 텍스트를 문장 단위로 나눠서 자연스럽게 구성해주세요\n"
        "4. 의미가 불분명한 부분은 생략하지 말고 그대로 유지해주세요\n"
        "\n텍스트:\n" + raw_text
    )
    # openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4096,
        )
        refined = response.choices[0].message.content.strip()
        return refined
    except Exception as e:
        return f"[GPT 후처리 오류] {e}\n{raw_text}"


async def stt_from_file(file_path: str = None) -> dict:
    """
    OpenAI Whisper API를 사용해 업로드된 음성 파일을 텍스트로 변환 (병렬 처리, 청크 분할, 후처리 포함)
    Whisper 결과를 GPT로 자연스럽게 다듬은 뒤, 청크 분할 및 오버랩 기능 적용
    """
    try:
        if not file_path or not os.path.exists(file_path):
            return {"text": "음성 파일이 존재하지 않습니다."}
        # 1. 오디오 파일 청크 분할
        chunk_length_sec = 150  # 2.5분
        overlap_sec = 4
        chunk_paths = split_audio_to_chunks(file_path, chunk_length_sec, overlap_sec)
        
        # 2. 병렬로 Whisper API 호출
        # max_workers = min(10, len(chunk_paths))
        # chunk_results = [None] * len(chunk_paths)
        # with ThreadPoolExecutor(max_workers=max_workers) as executor:
        #     future_to_idx = {executor.submit(transcribe_chunk, chunk_paths[i]): i for i in range(len(chunk_paths))}
        #     for future in as_completed(future_to_idx):
        #         idx = future_to_idx[future]
        #         chunk_results[idx] = future.result()
        tasks = [transcribe_chunk(chunk_path) for chunk_path in chunk_paths]
        chunk_results = await asyncio.gather(*tasks)
        
        # 임시 청크 파일 삭제
        for p in chunk_paths:
            try:
                os.remove(p)
            except Exception:
                pass
                
        # 3. Whisper 전체 결과 합치기 (겹침 제거 X, 원본 합침)
        whisper_full_text = " ".join(chunk_results)
        
        # 4. GPT로 자연스럽게 다듬기
        refined_text = await gpt_refine_text(whisper_full_text)
        
        # 5. 다듬어진 텍스트를 기존 청크 분할/오버랩 함수에 넘김
        chunks = split_sentences_with_overlap(refined_text)
        
        # 업로드된 파일명 기준으로 txt_path 생성
        base = os.path.splitext(os.path.basename(file_path))[0]
        txt_path = f"{base}.txt"
        async with aiofiles.open(txt_path, "w", encoding="utf-8") as f:
            await f.write(refined_text)
            
        return {"text": refined_text, "chunks": chunks}
    except Exception as e:
        return {"text": f"STT 변환 중 오류 발생: {e}"}

        