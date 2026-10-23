// 远程终端由独立服务 claude-terminal-demo 提供（nginx 把 /cli-demo/ 反代到 127.0.0.1:18089），
// 自带口令登录和单写者控制；这里只用同源 iframe 嵌进来，不经过翻译后端。
export function TerminalFeature() {
  return (
    <iframe
      src="/cli-demo/"
      title="远程终端"
      className="block h-full w-full border-0 bg-[#19171e]"
    />
  );
}
