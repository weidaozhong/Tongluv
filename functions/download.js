export async function onRequest(context) {
  // 每次发布新版本时，GitHub Actions 会自动替换此处的最新版直链 (供国内用户高速下载)
  const gitHubDownloadUrl = "https://github.com/weidaozhong/Tongluv/releases/download/v1.0.3/xiaotong-v1.0.3.exe";
  
  // GitHub 官方 Releases 列表页面 (供海外用户自由挑选版本)
  const gitHubReleasesPage = "https://github.com/weidaozhong/Tongluv/releases";
  
  // 获取请求用户的国家/地区代码 (Cloudflare 自动提供)
  const country = context.request.headers.get("CF-IPCountry");
  
  // 如果不是中国大陆 (CN) 用户，直接 302 重定向到 GitHub 官方 Releases 列表页面，让其自由选择版本
  if (country && country !== "CN") {
    return Response.redirect(gitHubReleasesPage, 302);
  }
  
  // 如果是中国大陆 (CN) 用户，302 重定向到国内高速加速节点直接下载最新版
  const cnSpeedUrl = `https://ghfast.top/${gitHubDownloadUrl}`;
  return Response.redirect(cnSpeedUrl, 302);
}
