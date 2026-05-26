export async function onRequest(context) {
  const gitHubDownloadUrl = "https://github.com/weidaozhong/Tongluv/releases/download/v1.0.1/xiaotong.exe";
  
  // 获取请求用户的国家/地区代码 (Cloudflare 自动提供)
  const country = context.request.headers.get("CF-IPCountry");
  
  // 如果不是中国大陆 (CN) 用户，直接 302 重定向到 GitHub 官方原始下载链接
  if (country && country !== "CN") {
    return Response.redirect(gitHubDownloadUrl, 302);
  }
  
  // 如果是中国大陆 (CN) 用户，302 重定向到信誉极高、不报警告的公益高速加速节点 (moeyy 代理)
  // 这能彻底打破 Cloudflare 免费版对国内用户的越洋限速瓶颈
  const cnSpeedUrl = `https://github.moeyy.xyz/${gitHubDownloadUrl}`;
  return Response.redirect(cnSpeedUrl, 302);
}
