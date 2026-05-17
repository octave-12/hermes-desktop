#!/bin/bash
# 同步 Wiki 到 GitHub 脚本
# 使用方法：在能够访问 GitHub 的环境下运行此脚本

set -e

echo "开始同步 Wiki 到 GitHub..."

# 1. 克隆 GitHub Wiki 仓库
if [ -d "github-wiki-temp" ]; then
    rm -rf github-wiki-temp
fi

git clone https://github.com/octave-12/hermes-desktop.wiki.git github-wiki-temp
cd github-wiki-temp

# 2. 从 Gitee Wiki 同步内容
# 首先克隆 Gitee Wiki 作为参考
if [ -d "../gitee-wiki-ref" ]; then
    rm -rf ../gitee-wiki-ref
fi
git clone https://gitee.com/octave-12/hermes-desktop.wiki.git ../gitee-wiki-ref

# 3. 复制所有 Wiki 文件
cp -r ../gitee-wiki-ref/* .

# 4. 提交并推送
git add .
git status

if git diff --cached --quiet; then
    echo "没有变更需要提交"
else
    git commit -m "同步 Gitee Wiki 最新内容

$(date '+%Y-%m-%d %H:%M:%S')

🤖 Auto synced from Gitee"
    git push origin master
    echo "✅ Wiki 已成功同步到 GitHub"
fi

# 清理
cd ..
rm -rf github-wiki-temp gitee-wiki-ref

echo "完成！"
