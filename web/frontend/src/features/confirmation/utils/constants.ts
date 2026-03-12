/**
 * 分段确认工作流 - 常量配置
 */

/**
 * 工作流配置
 */
export const WORKFLOW_CONFIG = {
  // 轮询间隔（毫秒）
  POLLING_INTERVAL: 2000,

  // 确认进度自动保存间隔（毫秒）
  AUTO_SAVE_INTERVAL: 5000,

  // 最大重试次数
  MAX_RETRIES: 3,

  // 批量操作批次大小
  BATCH_SIZE: 10,

  // 缓存过期时间（毫秒）
  CACHE_EXPIRY: 5 * 60 * 1000, // 5分钟

  // 最大导入文件大小（字节）
  MAX_IMPORT_FILE_SIZE: 10 * 1024 * 1024, // 10MB

  // 支持的文件类型
  SUPPORTED_FILE_TYPES: ['.md', '.txt'],

  // Toast显示时长（毫秒）
  TOAST_DURATION: {
    SUCCESS: 2000,
    ERROR: 5000,
    INFO: 3000,
    WARNING: 4000,
  },

  // 动画时长（毫秒）
  ANIMATION_DURATION: {
    FAST: 150,
    NORMAL: 300,
    SLOW: 500,
  },
} as const;

/**
 * UI配置
 */
export const UI_CONFIG = {
  // 左侧面板宽度百分比
  SOURCE_PANEL_WIDTH: 30,

  // 版本列表每页显示数量
  VERSIONS_PER_PAGE: 10,

  // 进度条更新间隔（毫秒）
  PROGRESS_UPDATE_INTERVAL: 500,

  // 滚动行为
  SCROLL_BEHAVIOR: {
    SMOOTH: 'smooth' as const,
    AUTO: 'auto' as const,
  },

  // 键盘导航
  KEYBOARD_NAVIGATION: {
    CONFIRM: 'Ctrl+Enter',
    NEXT: 'Ctrl+ArrowDown',
    PREV: 'Ctrl+ArrowUp',
    CANCEL: 'Escape',
  },
} as const;

/**
 * 翻译质量评分阈值
 */
export const QUALITY_THRESHOLDS = {
  EXCELLENT: 9.0,
  GOOD: 7.5,
  ACCEPTABLE: 6.0,
  POOR: 4.0,
} as const;

/**
 * 文本长度限制
 */
export const TEXT_LIMITS = {
  // 段落最大长度
  MAX_PARAGRAPH_LENGTH: 5000,

  // 术语最大长度
  MAX_TERM_LENGTH: 100,

  // 版本名称最大长度
  MAX_VERSION_NAME_LENGTH: 100,

  // 词义说明最大长度
  MAX_NOTE_LENGTH: 500,
} as const;

/**
 * 正则表达式
 */
export const REGEX_PATTERNS = {
  // 邮箱
  EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,

  // URL
  URL: /^https?:\/\/[^\s/$.?#].[^\s]*$/,

  // 中文
  CHINESE: /[\u4e00-\u9fa5]/,

  // 英文单词
  ENGLISH_WORD: /\b[a-zA-Z]+\b/g,

  // 数字
  NUMBER: /\d+/,

  // Markdown标题
  MARKDOWN_HEADING: /^#{1,6}\s+/,

  // Markdown代码块
  MARKDOWN_CODE: /```[\s\S]*?```/,

  // Markdown链接
  MARKDOWN_LINK: /\[([^\]]+)\]\(([^)]+)\)/,
} as const;

/**
 * 错误消息
 */
export const ERROR_MESSAGES = {
  NETWORK_ERROR: '网络连接失败，请检查网络设置',
  TIMEOUT_ERROR: '请求超时，请稍后重试',
  NOT_FOUND_ERROR: '资源未找到',
  UNAUTHORIZED_ERROR: '未授权，请重新登录',
  VALIDATION_ERROR: '输入数据验证失败',
  UNKNOWN_ERROR: '发生未知错误',
  PROJECT_NOT_FOUND: '项目未找到',
  PARAGRAPH_NOT_FOUND: '段落未找到',
  VERSION_NOT_FOUND: '版本未找到',
  IMPORT_FAILED: '导入失败，请检查文件格式',
  EXPORT_FAILED: '导出失败，请稍后重试',
} as const;

/**
 * 成功消息
 */
export const SUCCESS_MESSAGES = {
  PARAGRAPH_CONFIRMED: '译文已确认',
  TERMS_UPDATED: '术语已更新',
  VERSION_IMPORTED: '参考译文导入成功',
  VERSION_DELETED: '版本已删除',
  TRANSLATION_COMPLETED: '翻译完成',
  EXPORT_SUCCESS: '导出成功',
  ALIGNMENT_COMPLETED: '对齐完成',
} as const;

/**
 * 确认消息
 */
export const CONFIRM_MESSAGES = {
  DELETE_VERSION: '确定要删除此版本吗？',
  SKIP_PARAGRAPH: '确定要跳过此段落吗？',
  RESET_CHANGES: '确定要重置所有更改吗？',
  CANCEL_TRANSLATION: '确定要取消翻译吗？',
  CLEAR_EDIT: '确定要清空编辑内容吗？',
} as const;

/**
 * 提示消息
 */
export const INFO_MESSAGES = {
  AUTO_SAVE: '更改已自动保存',
  TERM_DETECTED: '检测到术语变更，已自动更新术语表',
  ALIGNMENT_HINT: '系统已自动对齐大部分段落，请手动调整未匹配的部分',
  SHORTCUT_HINT: '使用快捷键可以大幅提高效率',
  PROGRESS_HINT: '翻译进度已保存',
} as const;

/**
 * 工作流状态映射
 */
export const WORKFLOW_STATUS_MAP = {
  loading: '加载中',
  translating: '翻译中',
  ready: '就绪',
  complete: '完成',
} as const;

/**
 * 段落状态映射
 */
export const PARAGRAPH_STATUS_MAP = {
  pending: '待翻译',
  translating: '翻译中',
  translated: '已翻译',
  reviewing: '审阅中',
  modified: '已修改',
  approved: '已确认',
} as const;

/**
 * 颜色映射
 */
export const STATUS_COLORS = {
  pending: 'bg-gray-100 text-gray-800',
  translating: 'bg-blue-100 text-blue-800',
  translated: 'bg-yellow-100 text-yellow-800',
  reviewing: 'bg-purple-100 text-purple-800',
  modified: 'bg-orange-100 text-orange-800',
  approved: 'bg-green-100 text-green-800',
} as const;
