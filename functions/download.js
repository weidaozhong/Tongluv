export async function onRequest(context) {
  const downloadUrl = "https://github.com/weidaozhong/Tongluv/releases/download/v1.0.1/xiaotong-v1.0.1.exe";
  const fileName = "xiaotong-v1.0.1.exe";
  
  try {
    const response = await fetch(downloadUrl);
    if (!response.ok) {
      return new Response("无法从源站获取文件", { status: response.status });
    }
    const newHeaders = new Headers(response.headers);
    newHeaders.set("Content-Disposition", `attachment; filename="${fileName}"`);
    newHeaders.set("Access-Control-Allow-Origin", "*");
    
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: newHeaders
    });
  } catch (err) {
    return new Response("下载代理服务暂时不可用: " + err.message, { status: 500 });
  }
}
