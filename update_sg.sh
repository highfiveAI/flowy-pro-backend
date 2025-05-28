#!/bin/bash

PORT=22                              # SSH 포트 (필요시 변경)
PROTOCOL="tcp"

# 1. 기존에 등록된 github-actions IP 제거 (선택)
echo "Revoking old GitHub Actions IP permissions..."

# ip-permission 정보 중에 github-actions 설명 있는 규칙 찾아서 삭제
# --query 옵션 등으로 추출 가능, 간단히 모든 인바운드 중 PORT+PROTOCOL만 필터링해서 제거 예시
EXISTING_CIDRS=$(aws ec2 describe-security-groups --group-ids $SECURITY_GROUP_ID --query "SecurityGroups[0].IpPermissions[?FromPort==\`$PORT\` && ToPort==\`$PORT\` && IpProtocol=='$PROTOCOL'].IpRanges[].CidrIp" --output text)

for cidr in $EXISTING_CIDRS; do
  echo "Revoking $cidr ..."
  aws ec2 revoke-security-group-ingress --group-id $SECURITY_GROUP_ID --protocol $PROTOCOL --port $PORT --cidr $cidr
done

# 2. GitHub Actions IP 가져오기
echo "Fetching GitHub Actions IP ranges..."
GITHUB_IPS=$(curl -s https://api.github.com/meta | jq -r '.actions[]')

# 3. 새 IP 목록 보안 그룹에 추가
for cidr in $GITHUB_IPS; do
  echo "Authorizing $cidr ..."
  aws ec2 authorize-security-group-ingress --group-id $SECURITY_GROUP_ID --protocol $PROTOCOL --port $PORT --cidr $cidr --description "github-actions"
done

echo "Update completed."
