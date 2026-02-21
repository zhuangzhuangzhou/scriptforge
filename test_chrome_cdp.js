#!/usr/bin/env node
const CDP = require('chrome-remote-interface');

async function test() {
  let client;
  try {
    // 直接连接到默认标签页
    client = await CDP({ port: 9222 });
    const { Page, Runtime, Console, Network } = client;

    // 启用所需域
    await Promise.all([
      Page.enable(),
      Runtime.enable(),
      Console.enable(),
      Network.enable()
    ]);

    // 收集控制台日志
    const logs = [];
    Console.messageAdded((msg) => {
      logs.push({ type: msg.type, text: msg.text, url: msg.url, line: msg.line });
    });

    // 收集网络请求和响应
    const requests = [];
    const responses = [];
    Network.requestWillBeSent((params) => {
      requests.push(params.request.url);
    });
    Network.responseReceived((params) => {
      responses.push({
        url: params.response.url,
        status: params.response.status
      });
    });

    // 导航到页面
    console.log('🌐 正在打开页面: http://localhost:5173');
    await Page.navigate({ url: 'http://localhost:5173' });

    // 等待页面加载完成
    await Page.loadEventFired();
    await new Promise(resolve => setTimeout(resolve, 5000));

    // 获取页面信息
    const title = await Runtime.evaluate({ expression: 'document.title' });
    const url = await Runtime.evaluate({ expression: 'window.location.href' });
    const body = await Runtime.evaluate({ expression: 'document.body.innerText.substring(0, 500)' });

    console.log(`\n========== 页面信息 ==========`);
    console.log(`📄 标题: ${title.result.value}`);
    console.log(`🔗 URL: ${url.result.value}`);
    console.log(`📝 内容预览:\n${body.result.value || '(空)'}`);

    // 检查控制台错误
    const errors = logs.filter(l => l.type === 'error');
    console.log(`\n========== 控制台错误 ==========`);
    if (errors.length > 0) {
      errors.forEach(e => console.log(`🚨 ${e.text}`));
    } else {
      console.log('✅ 无错误');
    }

    // 检查失败的请求
    const failed = responses.filter(r => r.status >= 400);
    console.log(`\n========== 失败请求 ==========`);
    if (failed.length > 0) {
      failed.forEach(f => console.log(`❌ ${f.status} ${f.url}`));
    } else {
      console.log('✅ 无失败请求');
    }

    await client.close();
    console.log('\n✅ 测试完成');
  } catch (err) {
    console.error('❌ 错误:', err.message);
    if (client) await client.close();
  }
}

test();
