/** 网页版翻译用的模型（模型别名）；空串 = 后端默认模型。真正开始翻译时才记下来，下次默认用它 */
const KEY = 'translation.articles.webModel';

export function loadWebModel(): string {
  try {
    return localStorage.getItem(KEY) ?? '';
  } catch {
    return '';
  }
}

export function saveWebModel(model: string): void {
  try {
    if (model) localStorage.setItem(KEY, model);
    else localStorage.removeItem(KEY);
  } catch {
    // 隐私模式等存不了就算了
  }
}
