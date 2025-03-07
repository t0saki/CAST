#!/bin/bash
set -e

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 默认不清理
CLEAN=false

# 处理命令行参数
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --clean) CLEAN=true; shift ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

echo -e "${YELLOW}[INFO] 开始构建和部署 Little Vote 服务...${NC}"

# 构建 Docker 镜像
echo -e "${YELLOW}[INFO] 构建 Docker 镜像...${NC}"
docker build -t little-vote:latest .

# 确认 Kubernetes 集群连接
echo -e "${YELLOW}[INFO] 检查 Kubernetes 集群连接...${NC}"
kubectl cluster-info

# 如果需要清理旧部署
if [ "$CLEAN" = true ]; then
  echo -e "${YELLOW}[INFO] 正在清理旧的部署...${NC}"
  
  # 检查命名空间是否存在
  if kubectl get namespace little-vote &> /dev/null; then
    # 删除命名空间中的所有资源
    echo -e "${YELLOW}[INFO] 删除命名空间 little-vote 中的所有资源...${NC}"
    kubectl delete -k k8s/ --ignore-not-found=true
    
    # 等待资源删除完成
    echo -e "${YELLOW}[INFO] 等待资源删除完成...${NC}"
    kubectl wait --for=delete namespace/little-vote --timeout=120s 2>/dev/null || true
  else
    echo -e "${YELLOW}[INFO] 命名空间 little-vote 不存在，无需清理${NC}"
  fi
fi

# 部署到 Kubernetes
echo -e "${YELLOW}[INFO] 部署到 Kubernetes...${NC}"
kubectl apply -k k8s/

# 等待服务启动
echo -e "${YELLOW}[INFO] 等待服务启动...${NC}"
kubectl -n little-vote wait --for=condition=available --timeout=300s deployment/main-service deployment/ticket-generator deployment/vote-consumer

# 获取服务信息
echo -e "${GREEN}[SUCCESS] 部署完成!${NC}"
echo -e "${YELLOW}[INFO] 获取服务信息...${NC}"
kubectl -n little-vote get all

echo -e "${GREEN}[SUCCESS] 部署脚本执行完毕!${NC}" 

echo -e "${YELLOW}[提示] 如需完全重新部署，请运行: ./build-and-deploy.sh --clean${NC}"