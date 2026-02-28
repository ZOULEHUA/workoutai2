# workoutai2

AI 健身计划 MVP（支持体态分析、饮食碳循环表、PDF导出、内测码机制）。

## 功能
- 上传正面照 + 背面照。
- 输入客户信息（姓名、性别、身高、体重、目标）或粘贴文字后一键解析自动填充。
- 支持两种方案：
  - 含力量训练（按碳循环周期输出）
  - 不含力量训练（纯饮食计划）
- 输出：
  - 体态分析摘要（含薄弱肌群提示）
  - 阶段化饮食表（宏量营养 + 食材克重）
  - 专属 PDF 下载
- 内测码机制：只有有效内测码可调用生成计划接口。
- 管理端可批量生成数字内测码。

## 快速运行
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

浏览器访问：`http://localhost:8000`

## 环境变量
- `ADMIN_SECRET`：管理端生成内测码时校验的密钥。

示例：
```bash
export ADMIN_SECRET='your-admin-secret'
```

## API
### 1) 生成内测码
`POST /api/beta/generate`

```json
{
  "admin_secret": "your-admin-secret",
  "count": 5
}
```

### 2) 生成计划
`POST /api/plan`（`multipart/form-data`）

关键字段：
- `beta_code`
- `name`
- `gender`
- `height_cm`
- `weight_kg`
- `goal`
- `strength_training` (true/false)
- `front_image`
- `back_image`

返回 `plan` 和 `pdf_url`。

## 说明
- 代码中未硬编码任何第三方模型密钥。
- 当前为可直接跑通的 MVP，可在此基础上接入你指定的读图大模型。
