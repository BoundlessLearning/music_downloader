# 基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY ./music_service /app

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建媒体目录
RUN mkdir -p /media

# 暴露默认端口 16333
EXPOSE 16333

# 设置默认环境变量
ENV DJANGO_PORT=16333

# 启动命令，使用动态端口
CMD python manage.py runserver 0.0.0.0:${DJANGO_PORT}
