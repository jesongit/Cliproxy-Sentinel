# Cliproxy Sentinel

`Cliproxy Sentinel` 是一个用于维护 CLIProxyAPI `codex` 账号池健康度的自动化守护服务。

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![Status](https://img.shields.io/badge/Status-Active-success)

核心能力：
1. 轮询账号池并识别无效账号
2. 自动清理无效账号
3. 自动注册补齐到目标数量
4. 注册后以内存方式上传 token（默认不落盘）

## 功能特性

1. 面向账号池的闭环维护：巡检、清理、补齐一体化。
2. 配置集中在根目录 `config.yaml`，部署与修改更直观。
3. 注册逻辑已内置在项目源码中，无需外部注册仓库。
4. 默认内存上传 token，降低敏感文件落盘风险。
5. 支持本地运行和 Docker Compose 部署两种模式。

## 快速开始

```bash
cp config.example.yaml config.yaml
python -m pip install -r requirements.txt
python -m pip install -e .
python -m cliproxyapi.app --config config.yaml --once
```

## 项目结构

```text
cliproxyapi/
├─ config.yaml
├─ config.example.yaml
├─ config.retry-once.yaml
├─ config.trigger-once.yaml
├─ docker-compose.yml
├─ Dockerfile
├─ src/cliproxyapi/
│  ├─ app.py
│  ├─ settings.py
│  ├─ logging_setup.py
│  ├─ monitor/
│  │  ├─ account_rules.py
│  │  └─ scheduler.py
│  ├─ cliproxy/client.py
│  └─ registration/registrar.py
└─ tests/
```

## 环境要求

1. Python 3.10+
2. 可访问 CLIProxyAPI 管理接口
3. 可用的 IMAP 邮箱（用于验证码）

## 本地运行

### 1) 安装依赖

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

### 2) 准备配置

```bash
cp config.example.yaml config.yaml
```

最少需要填写以下字段：
1. `cliproxy.api_base`
2. `cliproxy.management_key`
3. `registration.imap.host`
4. `registration.imap.username`
5. `registration.imap.password`

### 3) 启动方式

单轮执行（调试）：

```bash
python -m cliproxyapi.app --config config.yaml --once
```

说明：`--once` 会强制新增 1 个账号，不按目标数量做补齐计算。

常驻执行（生产）：

```bash
python -m cliproxyapi.app --config config.yaml
```

## Docker 部署

### 1) 准备配置

```bash
cp config.example.yaml config.yaml
```

### 2) 启动服务

```bash
docker compose up -d --build
```

### 3) 查看日志

```bash
docker compose logs -f cliproxyapi
```

### 4) 停止服务

```bash
docker compose down
```

说明：
1. 当前镜像已包含内置注册模块，无需额外挂载注册仓库。

## 测试

```bash
python -m pytest -q
```

## 常见问题（FAQ）

### 1) 注册流程报错如何定位？

先查看容器日志确认失败阶段（OAuth、邮箱验证码、上传 token）：

```bash
docker compose logs -f cliproxyapi
```

### 2) 为什么默认不把 token 写入本地文件？

项目默认使用 `memory_json` 上传模式，目的是减少敏感信息在磁盘上的残留。如果你需要排查上传失败，可开启：

```yaml
debug:
  save_failed_upload_payload: true
```

### 3) 如何先验证配置是否正确？

建议先执行单轮模式：

```bash
python -m cliproxyapi.app --config config.yaml --once
```

单轮执行成功后再切换常驻模式。

## 路线图

1. 增加健康检查端点，便于容器探针接入。
2. 增加更细粒度的告警与重试策略配置。
3. 补充 CI 流程与镜像自动构建发布。
4. 输出更完整的运行指标与可观测性文档。

## 贡献

欢迎提交 Issue 或 PR。提交前建议先本地执行：

```bash
python -m pytest -q
```

## 许可证

当前仓库未声明许可证；如需开源发布，建议尽快补充 `LICENSE` 文件。

## 配置补充说明

1. `upload.mode` 固定使用 `memory_json`，注册后直接上传 token 载荷。
2. `debug.save_failed_upload_payload=true` 时，会把失败请求保存到 `debug.failed_payload_dir`，便于排查。
