const HASHTAG_PATTERN = /#[A-Za-z0-9_\-\u3400-\u9fff]+/g;
const TAG_ONLY_LINE_PATTERN =
  /^(?:\s*#[A-Za-z0-9_\-\u3400-\u9fff]+\s*[,，、|｜·]?\s*)+$/;

const GENERIC_HASHTAGS = new Set([
  '#科技',
  '#科技资讯',
  '#行业观察',
  '#产业趋势',
  '#热点观察',
]);

type TopicRule = {
  tag: string;
  all: RegExp[];
};

const TOPIC_RULES: TopicRule[] = [
  {
    tag: '#NVIDIABlackwell',
    all: [/\bNVIDIA\b|英伟达/i, /\bBlackwell\b|\bB(?:100|200|300)\b/i],
  },
  {
    tag: '#大模型推理',
    all: [
      /\bLLMs?\b|large language model|大模型|语言模型/i,
      /\binference\b|\bserving\b|\btokens?\b|推理|吞吐/i,
    ],
  },
  {
    tag: '#AI芯片',
    all: [
      /artificial intelligence|人工智能|(?<![A-Za-z0-9])AI(?![A-Za-z0-9])/i,
      /\b(?:GPU|NPU|TPU|ASIC)\b|芯片|accelerator|加速器/i,
    ],
  },
  {
    tag: '#先进制程',
    all: [/\b(?:1[024]|[2-7])\s*nm\b|\bEUV\b|先进制程|光刻/i],
  },
  {
    tag: '#晶圆代工',
    all: [/\bfoundry\b|晶圆代工|晶圆厂/i],
  },
  {
    tag: '#AI基础设施',
    all: [/\bAI infrastructure\b|\bGPU cluster\b|AI基础设施|GPU集群/i],
  },
  {
    tag: '#OpenAI',
    all: [/\bOpenAI\b|\bChatGPT\b|\bCodex\b/i],
  },
  {
    tag: '#Claude',
    all: [/\bAnthropic\b|\bClaude\b/i],
  },
  {
    tag: '#GoogleGemini',
    all: [/\bGoogle Gemini\b|\bGemini\b/i],
  },
  {
    tag: '#英伟达',
    all: [/\bNVIDIA\b|英伟达|Jensen Huang|黄仁勋/i],
  },
  {
    tag: '#台积电',
    all: [/\bTSMC\b|台积电/i],
  },
  {
    tag: '#ASML',
    all: [/\bASML\b/i],
  },
  {
    tag: '#HBM',
    all: [/\bHBM(?:[234]E?)?\b|高带宽内存/i],
  },
  {
    tag: '#GPU',
    all: [/\bGPUs?\b|图形处理器/i],
  },
];

const PRODUCT_PATTERN =
  /\b(?:H100|H200|B100|B200|B300|GB200|GB300|MI300X|MI325X|MI350|TPUv\d+|GPT-\d+(?:\.\d+)?|Llama\s*\d+(?:\.\d+)?|Claude\s*\d+(?:\.\d+)?|Gemini\s*\d+(?:\.\d+)?)\b/gi;

export function normalizeHashtag(value: string): string | null {
  const normalized = value
    .trim()
    .replace(/^#+/, '')
    .replace(/\s+/g, '')
    .replace(/[^\p{L}\p{N}_-]/gu, '');
  if (!normalized) return null;
  const hashtag = `#${normalized}`;
  return GENERIC_HASHTAGS.has(hashtag) ? null : hashtag;
}

export function isGenericHashtag(value: string): boolean {
  const normalized = `#${value.trim().replace(/^#+/, '')}`;
  return GENERIC_HASHTAGS.has(normalized);
}

export function splitPostContent(content: string): {
  body: string;
  hashtags: string[];
} {
  const lines = content.trimEnd().split('\n');
  const hashtags: string[] = [];

  while (lines.length > 0) {
    const line = lines.at(-1)?.trim() ?? '';
    if (!TAG_ONLY_LINE_PATTERN.test(line)) break;
    const lineTags = line.match(HASHTAG_PATTERN) ?? [];
    hashtags.unshift(...lineTags);
    lines.pop();
  }

  return {
    body: lines.join('\n').trimEnd(),
    hashtags: Array.from(
      new Set(
        hashtags
          .map(normalizeHashtag)
          .filter((tag): tag is string => Boolean(tag))
      )
    ).slice(0, 8),
  };
}

export function suggestSpecificHashtags(
  sourceText: string,
  translatedBody: string
): string[] {
  const content = `${sourceText}\n${translatedBody}`;
  const matched = TOPIC_RULES
    .filter(rule => rule.all.every(pattern => pattern.test(content)))
    .map(rule => rule.tag);
  const products = Array.from(content.matchAll(PRODUCT_PATTERN), match =>
    normalizeHashtag(match[0])
  ).filter((tag): tag is string => Boolean(tag));

  return Array.from(new Set([...matched, ...products])).slice(0, 8);
}

export function composeXiaohongshuPost(
  title: string,
  body: string,
  hashtags: string[]
): string {
  const parts = [title.trim(), body.trim()].filter(Boolean);
  const normalizedTags = Array.from(
    new Set(
      hashtags
        .map(normalizeHashtag)
        .filter((tag): tag is string => Boolean(tag))
    )
  );
  if (normalizedTags.length > 0) {
    parts.push(normalizedTags.join(' '));
  }
  return parts.join('\n\n');
}
