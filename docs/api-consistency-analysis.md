# API 路由一致性分析报告

## 执行摘要

分析了 `src/api/routers/` 目录下所有路由文件，发现以下关键问题：

- **速率限制覆盖率**: 仅 4/30+ 端点有速率限制（13%）
- **输入验证**: 大部分模型有基本验证，但缺少统一的大小限制
- **错误处理**: 混合使用自定义异常和 HTTPException
- **参数命名**: 存在不一致，部分端点缺少 Request 参数导致 slowapi 失效

---

## 1. 速率限制一致性分析

### ✅ 已有速率限制的端点（4个）

| 端点 | 限制 | 文件 |
|------|------|------|
| `POST /api/translate/post` | 20/minute | translate_posts.py:34 |
| `POST /api/translate/post/optimize` | 20/minute | translate_posts.py:71 |
| `POST /api/generate/title` | 20/minute | translate_posts.py:109 |
| `POST /api/tools/translate` | 20/minute | tools_translate.py:23 |
| `POST /api/tools/email-reply` | 10/minute | tools_email.py:38 |
| `POST /api/wechat/format` | 1000/minute | wechat_format.py:76 |

### ❌ 缺少速率限制的端点（按优先级分类）

#### 🔴 高优先级（公开端点，易被滥用）

1. **Slack 相关端点** (slack_process.py, slack_compose.py, slack_refine.py)
   - `POST /api/slack/process` - 处理 Slack 消息，调用 LLM
   - `POST /api/slack/compose` - 生成 Slack 回复，调用 LLM
   - `POST /api/slack/refine` - 优化 Slack 回复，调用 LLM
   - **建议**: 添加 `@limiter.limit("20/minute")`

2. **项目翻译端点** (translate_projects.py)
   - `POST /api/projects/{project_id}/analyze` - 项目分析，调用 LLM
   - `POST /api/projects/{project_id}/sections/{section_id}/analyze` - 章节分析，调用 LLM
   - `POST /api/projects/{project_id}/sections/{section_id}/translate_all` - 批量翻译
   - `POST /api/projects/{project_id}/translate-stream` - 全文翻译（SSE）
   - `POST /api/projects/{project_id}/translate-four-step` - 四步法翻译（SSE）
   - **建议**: 添加 `@limiter.limit("10/minute")` （资源密集型操作）

3. **段落翻译端点** (projects_paragraphs.py)
   - `POST /api/projects/{project_id}/sections/{section_id}/paragraphs/{paragraph_id}/translate` - 单段翻译
   - `POST /api/projects/{project_id}/sections/{section_id}/paragraphs/{paragraph_id}/direct-translate` - 直接翻译
   - `POST /api/projects/{project_id}/sections/{section_id}/paragraphs/{paragraph_id}/word-meaning` - 词义查询
   - `POST /api/projects/{project_id}/sections/{section_id}/translate_batch` - 批量翻译
   - **建议**: 添加 `@limiter.limit("30/minute")`

4. **确认翻译端点** (confirmation_translation.py)
   - `POST /api/{project_id}/translate-all` - 启动翻译
   - `POST /api/{project_id}/paragraph/{paragraph_id}/retranslate` - 重新翻译
   - `POST /api/{project_id}/consistency-review` - 一致性审查，调用 LLM
   - **建议**: 添加 `@limiter.limit("20/minute")`

#### 🟡 中优先级（内部端点，但仍需保护）

5. **术语表管理** (glossary.py, project_glossary.py)
   - `POST /api/glossary` - 添加全局术语
   - `POST /api/glossary/batch` - 批量更新术语
   - `POST /api/projects/{project_id}/term-review/prepare` - 准备术语审查，调用 LLM
   - **建议**: 添加 `@limiter.limit("60/minute")`

6. **项目管理** (projects_management.py)
   - `POST /api/projects` - 创建项目
   - `POST /api/projects/upload` - 上传项目文件
   - `POST /api/projects/{project_id}/export` - 导出项目
   - **建议**: 添加 `@limiter.limit("30/minute")`

#### 🟢 低优先级（读取端点，但建议添加宽松限制）

7. **GET 端点**
   - 所有 GET 端点建议添加 `@limiter.limit("300/minute")` 防止爬虫

---

## 2. 输入验证一致性分析

### ✅ 良好的输入验证示例

**translate_models.py** (translate_posts.py 使用):
```python
class PostTranslateRequest(BaseModel):
    content: str = Field(..., max_length=10000)  # ✅ 有大小限制
    custom_prompt: Optional[str] = Field(None, max_length=2000)  # ✅ 有大小限制
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content cannot be empty")
        if len(v.strip()) < 10:
            raise ValueError("Content too short")
        return v
```

**wechat_format.py**:
```python
class WechatFormatRequest(BaseModel):
    markdown: str = Field(..., max_length=10*1024*1024)  # ✅ 10MB 限制
    theme: str = "default"
    
    @field_validator('markdown')
    @classmethod
    def validate_markdown_size(cls, v: str) -> str:
        if len(v.encode('utf-8')) > MAX_MARKDOWN_SIZE:
            raise ValueError(f"Markdown content exceeds {MAX_MARKDOWN_SIZE} bytes")
        return v
```

### ❌ 缺少输入验证的模型

#### 🔴 高优先级（需要添加大小限制）

1. **projects_models.py**:
```python
class TranslateRequest(BaseModel):
    instruction: Optional[str] = None  # ❌ 无大小限制
    option_id: Optional[str] = None

class WordMeaningRequest(BaseModel):
    word: str  # ❌ 无大小限制
    query: str  # ❌ 无大小限制
    history: List[WordMeaningMessage] = Field(default_factory=list)  # ❌ 无长度限制

class UpdateParagraphRequest(BaseModel):
    translation: Optional[str] = None  # ❌ 无大小限制
    status: Optional[str] = None
```

**建议修复**:
```python
class TranslateRequest(BaseModel):
    instruction: Optional[str] = Field(None, max_length=2000)
    option_id: Optional[str] = Field(None, max_length=50)

class WordMeaningRequest(BaseModel):
    word: str = Field(..., max_length=200)
    query: str = Field(..., max_length=1000)
    history: List[WordMeaningMessage] = Field(default_factory=list, max_length=20)

class UpdateParagraphRequest(BaseModel):
    translation: Optional[str] = Field(None, max_length=50000)
    status: Optional[str] = Field(None, max_length=20)
```

2. **confirmation_models.py**:
```python
class ConfirmParagraphRequest(BaseModel):
    translation: str  # ❌ 无大小限制
    version_id: Optional[str] = None
    custom_edit: bool = False

class UpdateTermsRequest(BaseModel):
    changes: list[dict]  # ❌ 无长度限制

class RetranslateRequest(BaseModel):
    instruction: Optional[str] = None  # ❌ 无大小限制
    option_id: Optional[str] = None
```

**建议修复**:
```python
class ConfirmParagraphRequest(BaseModel):
    translation: str = Field(..., max_length=50000)
    version_id: Optional[str] = Field(None, max_length=100)
    custom_edit: bool = False

class UpdateTermsRequest(BaseModel):
    changes: list[dict] = Field(..., max_length=100)

class RetranslateRequest(BaseModel):
    instruction: Optional[str] = Field(None, max_length=2000)
    option_id: Optional[str] = Field(None, max_length=50)
```

3. **project_glossary.py**:
```python
class AddTermRequest(BaseModel):
    original: str  # ❌ 无大小限制
    translation: Optional[str] = None  # ❌ 无大小限制
    note: Optional[str] = None  # ❌ 无大小限制

class MatchTermsRequest(BaseModel):
    paragraph: str  # ❌ 无大小限制
    max_terms: int = 20  # ✅ 有默认值，但无范围限制
```

**建议修复**:
```python
class AddTermRequest(BaseModel):
    original: str = Field(..., max_length=200)
    translation: Optional[str] = Field(None, max_length=500)
    note: Optional[str] = Field(None, max_length=1000)

class MatchTermsRequest(BaseModel):
    paragraph: str = Field(..., max_length=10000)
    max_terms: int = Field(20, ge=1, le=100)
```

---

## 3. 错误处理一致性分析

### ✅ 统一使用自定义异常的文件

大部分文件正确使用了自定义异常：
- `BadRequestException` - 400 错误
- `NotFoundException` - 404 错误
- `ServiceUnavailableException` - 503 错误

**良好示例** (projects_paragraphs.py):
```python
if not validate_path_component(project_id):
    raise BadRequestException(detail="Invalid path component")

try:
    # ... 业务逻辑
except NotFoundException:
    raise
except FileNotFoundError:
    raise NotFoundException(detail="Project not found")
except RuntimeError as error:
    raise _to_bad_request(error, "Translation")
```

### ❌ 不一致的错误处理

1. **glossary.py:89** - 直接使用 HTTPException:
```python
def _find_existing_term(glossary, original: str) -> GlossaryTerm:
    existing = glossary.get_term(original)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Term '{original}' not found")  # ❌
    return existing
```

**建议修复**:
```python
def _find_existing_term(glossary, original: str) -> GlossaryTerm:
    existing = glossary.get_term(original)
    if not existing:
        raise NotFoundException(detail=f"Term '{original}' not found")  # ✅
    return existing
```

2. **project_glossary.py:122-128** - 混合使用 ValueError 和自定义异常:
```python
if request.action == "set_status" and request.status is None:
    raise ValueError("Batch action 'set_status' requires status")  # ❌ 应该用 BadRequestException
```

**建议修复**:
```python
if request.action == "set_status" and request.status is None:
    raise BadRequestException(detail="Batch action 'set_status' requires status")  # ✅
```

3. **生产环境错误信息泄露**

**良好示例** (projects_paragraphs.py:400-416):
```python
def _to_bad_request(error: Exception, action: str) -> BadRequestException:
    error_msg = str(error)
    logger.error(f"{action} failed: {error_msg}")
    
    # 生产环境不暴露详细错误信息
    if os.getenv("DEBUG") == "true":
        return BadRequestException(detail=f"{action} failed: {error_msg}")
    return BadRequestException(detail=f"{action} failed. Please try again or contact support.")
```

**需要改进的文件**:
- `translate_projects.py:87` - 直接暴露异常信息: `f"分析失败: {str(e)}"`
- `confirmation_translation.py:83` - 直接暴露异常信息: `f"Failed to start translation: {str(e)}"`
- `slack_refine.py:51` - 直接 raise 原始异常

---

## 4. 参数命名一致性分析

### ⚠️ slowapi 要求

slowapi 的 `@limiter.limit()` 装饰器要求：
- 第一个参数必须是 `request: Request`
- 否则无法提取客户端 IP 进行速率限制

### ✅ 正确的参数命名

**translate_posts.py:35**:
```python
@router.post("/translate/post", response_model=PostTranslateResponse)
@limiter.limit("20/minute")
async def translate_post(request: Request, body: PostTranslateRequest):  # ✅
    ...
```

**tools_email.py:39**:
```python
@router.post("/email-reply", response_model=EmailReplyResponse)
@limiter.limit("10/minute")
async def generate_email_reply(request: Request, body: EmailReplyRequest):  # ✅
    ...
```

### ❌ 缺少 Request 参数的端点

以下端点如果添加速率限制，需要先添加 `request: Request` 参数：

1. **slack_process.py:44**:
```python
async def process_slack_message(
    request: SlackProcessRequest,  # ❌ 参数名冲突
):
```

**建议修复**:
```python
@limiter.limit("20/minute")
async def process_slack_message(
    http_request: Request,  # ✅ 添加 Request 参数
    request: SlackProcessRequest,
):
```

2. **slack_compose.py:44**:
```python
async def compose_slack_message(
    request: SlackComposeRequest,  # ❌ 参数名冲突
):
```

**建议修复**:
```python
@limiter.limit("20/minute")
async def compose_slack_message(
    http_request: Request,  # ✅
    request: SlackComposeRequest,
):
```

3. **slack_refine.py:12**:
```python
async def refine_result(request: SlackRefineRequest) -> SlackRefineResponse:  # ❌
```

**建议修复**:
```python
@limiter.limit("20/minute")
async def refine_result(
    http_request: Request,  # ✅
    request: SlackRefineRequest
) -> SlackRefineResponse:
```

4. **translate_projects.py** - 所有端点都缺少 Request 参数:
```python
async def analyze_project(project_id: str):  # ❌
async def analyze_section(project_id: str, section_id: str):  # ❌
async def batch_translate_section(...):  # ❌
async def translate_full_document(...):  # ❌
async def translate_with_four_steps(
    project_id: str,
    http_request: Request,  # ✅ 这个有，但不是第一个参数
    pm: ProjectManagerDep,
    ...
):
```

**建议修复**:
```python
@limiter.limit("10/minute")
async def analyze_project(request: Request, project_id: str):  # ✅

@limiter.limit("10/minute")
async def analyze_section(request: Request, project_id: str, section_id: str):  # ✅

@limiter.limit("5/minute")
async def batch_translate_section(
    request: Request,  # ✅ 添加为第一个参数
    project_id: str,
    section_id: str,
    pm: ProjectManagerDep,
    ...
):
```

---

## 5. 其他发现

### 🔍 安全问题

1. **translate_posts.py:41-43** - 自定义 prompt 注入风险:
```python
if body.custom_prompt:
    if not os.getenv("ALLOW_CUSTOM_PROMPTS", "false").lower() == "true":
        raise BadRequestException(detail="Custom prompts are not allowed in production")
```
✅ 已有保护，但建议完全移除此功能或仅在开发环境启用。

2. **tools_email.py:24-34** - 输入清洗:
```python
def sanitize_email_input(text: str) -> str:
    """清洗邮件输入，防止 prompt 注入"""
    text = html.escape(text)
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    return text
```
✅ 良好实践，建议在其他接受用户输入的端点也应用类似清洗。

### 📊 性能问题

1. **wechat_format.py:76** - 速率限制过高:
```python
@limiter.limit("1000/minute")  # ⚠️ 每分钟 1000 次，可能过于宽松
```
建议降低到 `100/minute` 或 `200/minute`。

2. **translate_projects.py:329** - 长时间运行的 SSE 端点无速率限制:
```python
@router.post("/projects/{project_id}/translate-four-step")
async def translate_with_four_steps(...):  # ❌ 无速率限制
```
这是资源密集型操作，建议添加 `@limiter.limit("3/minute")`。

---

## 6. 修复优先级总结

### 🔴 立即修复（P0）

1. **添加速率限制到 Slack 端点** (slack_process.py, slack_compose.py, slack_refine.py)
   - 影响: 防止 LLM API 滥用
   - 工作量: 3 个文件，每个添加 2 行代码

2. **添加速率限制到项目翻译端点** (translate_projects.py)
   - 影响: 防止资源耗尽
   - 工作量: 5 个端点，每个添加 2 行代码

3. **修复 glossary.py 中的 HTTPException**
   - 影响: 错误处理一致性
   - 工作量: 1 处修改

### 🟡 近期修复（P1）

4. **添加输入验证到 projects_models.py**
   - 影响: 防止超大请求
   - 工作量: 5 个模型，每个添加 max_length

5. **添加输入验证到 confirmation_models.py**
   - 影响: 防止超大请求
   - 工作量: 3 个模型

6. **统一错误处理** (project_glossary.py, translate_projects.py)
   - 影响: 生产环境不泄露敏感信息
   - 工作量: 约 10 处修改

### 🟢 后续优化（P2）

7. **添加速率限制到段落翻译端点** (projects_paragraphs.py)
8. **添加速率限制到术语表管理端点** (glossary.py, project_glossary.py)
9. **添加速率限制到项目管理端点** (projects_management.py)
10. **降低 wechat_format.py 的速率限制**

---

## 7. 实施建议

### 阶段 1: 速率限制（1-2 天）

创建统一的速率限制配置文件:

```python
# src/api/middleware/rate_limit_config.py

RATE_LIMITS = {
    # LLM 密集型端点（最严格）
    "llm_heavy": "3/minute",      # 四步法翻译
    "llm_medium": "10/minute",    # 项目分析、批量翻译
    "llm_light": "20/minute",     # 单段翻译、帖子翻译
    
    # 数据操作端点
    "data_write": "30/minute",    # 创建、更新、删除
    "data_read": "300/minute",    # 查询、列表
    
    # 文件上传端点
    "file_upload": "10/minute",
}
```

### 阶段 2: 输入验证（1 天）

创建统一的验证常量:

```python
# src/api/routers/validation_constants.py

MAX_TEXT_SHORT = 200          # 短文本（标题、标签）
MAX_TEXT_MEDIUM = 2000        # 中等文本（指令、注释）
MAX_TEXT_LONG = 10000         # 长文本（帖子、段落）
MAX_TEXT_DOCUMENT = 50000     # 文档级文本（完整段落）
MAX_LIST_LENGTH = 100         # 列表最大长度
MAX_HISTORY_LENGTH = 20       # 历史记录最大长度
```

### 阶段 3: 错误处理（1 天）

创建统一的错误处理工具:

```python
# src/api/utils/error_handling.py

def sanitize_error_for_production(error: Exception, operation: str) -> str:
    """生产环境下清洗错误信息"""
    if os.getenv("DEBUG") == "true":
        return f"{operation} failed: {str(error)}"
    
    # 识别常见错误类型，返回友好信息
    error_msg = str(error).lower()
    if "429" in error_msg or "rate limit" in error_msg:
        return "API rate limit reached. Please try again later."
    if "timeout" in error_msg:
        return f"{operation} timed out. Please try again."
    
    return f"{operation} failed. Please contact support."
```

---

## 8. 测试建议

### 速率限制测试

```python
# tests/test_rate_limiting.py

async def test_rate_limit_enforcement():
    """测试速率限制是否生效"""
    for i in range(25):  # 超过 20/minute 限制
        response = await client.post("/api/translate/post", json={"content": "test"})
        if i < 20:
            assert response.status_code == 200
        else:
            assert response.status_code == 429
```

### 输入验证测试

```python
# tests/test_input_validation.py

async def test_oversized_input_rejected():
    """测试超大输入被拒绝"""
    oversized_content = "x" * 20000  # 超过 10000 限制
    response = await client.post("/api/translate/post", json={"content": oversized_content})
    assert response.status_code == 422
    assert "max_length" in response.json()["detail"][0]["type"]
```

---

## 附录: 完整端点清单

| 端点 | 方法 | 速率限制 | 输入验证 | 错误处理 | 优先级 |
|------|------|----------|----------|----------|--------|
| `/api/translate/post` | POST | ✅ 20/min | ✅ | ✅ | - |
| `/api/translate/post/optimize` | POST | ✅ 20/min | ✅ | ✅ | - |
| `/api/generate/title` | POST | ✅ 20/min | ✅ | ✅ | - |
| `/api/tools/translate` | POST | ✅ 20/min | ✅ | ✅ | - |
| `/api/tools/email-reply` | POST | ✅ 10/min | ✅ | ✅ | - |
| `/api/wechat/format` | POST | ✅ 1000/min | ✅ | ✅ | P2 (降低限制) |
| `/api/slack/process` | POST | ❌ | ✅ | ⚠️ | P0 |
| `/api/slack/compose` | POST | ❌ | ✅ | ⚠️ | P0 |
| `/api/slack/refine` | POST | ❌ | ✅ | ❌ | P0 |
| `/api/projects/{id}/analyze` | POST | ❌ | ❌ | ⚠️ | P0 |
| `/api/projects/{id}/sections/{sid}/analyze` | POST | ❌ | ❌ | ⚠️ | P0 |
| `/api/projects/{id}/sections/{sid}/translate_all` | POST | ❌ | ❌ | ⚠️ | P0 |
| `/api/projects/{id}/translate-stream` | POST | ❌ | ❌ | ⚠️ | P0 |
| `/api/projects/{id}/translate-four-step` | POST | ❌ | ❌ | ⚠️ | P0 |
| `/api/projects/{id}/sections/{sid}/paragraphs/{pid}/translate` | POST | ❌ | ⚠️ | ✅ | P1 |
| `/api/projects/{id}/sections/{sid}/paragraphs/{pid}/direct-translate` | POST | ❌ | ⚠️ | ✅ | P1 |
| `/api/projects/{id}/sections/{sid}/paragraphs/{pid}/word-meaning` | POST | ❌ | ⚠️ | ✅ | P1 |
| `/api/projects/{id}/sections/{sid}/translate_batch` | POST | ❌ | ⚠️ | ✅ | P1 |
| `/api/{id}/translate-all` | POST | ❌ | ❌ | ⚠️ | P1 |
| `/api/{id}/paragraph/{pid}/retranslate` | POST | ❌ | ⚠️ | ⚠️ | P1 |
| `/api/{id}/consistency-review` | POST | ❌ | ❌ | ⚠️ | P1 |
| `/api/glossary` | POST | ❌ | ⚠️ | ❌ | P1 |
| `/api/glossary/batch` | POST | ❌ | ⚠️ | ❌ | P1 |
| `/api/projects/{id}/term-review/prepare` | POST | ❌ | ❌ | ⚠️ | P1 |
| `/api/projects` | POST | ❌ | ❌ | ✅ | P2 |
| `/api/projects/upload` | POST | ❌ | ❌ | ✅ | P2 |

**图例**:
- ✅ = 已实现且良好
- ⚠️ = 部分实现或需改进
- ❌ = 缺失
- P0 = 立即修复
- P1 = 近期修复
- P2 = 后续优化
