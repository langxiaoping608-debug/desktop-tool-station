import http.server, json, os, socket, urllib.parse

PORT = int(os.environ.get('PORT', '8888'))
DESKTOP = os.environ.get('DESKTOP_TOOL_DIR', os.path.dirname(os.path.abspath(__file__)))
API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
API_URL = 'https://api.deepseek.com/chat/completions'

# 静态文件白名单
ALLOW = {'/dispatch_selfcontained.html', '/工单备注替换工具.html', '/话术组织.html',
         '/公交文件/汇编查询系统.html', '/公交综合查询系统.html'}

# AI 模板
TEMPLATES = {
    'lost': {
        'name': '失物招领',
        'prompt': '''你是杭州公交热线话术助手。请严格按以下格式组织碎片信息。

【模板格式】
{线路}路，{日期}{上车时间}{上车点}上车-{下车时间}下车{下车站}，遗失：{物品}。

【关键规则】
1. **日期**：如果碎片中包含日期（如"5月18日""5.18""今天""昨天"），必须提取并放在时间前面。没有则不写。
2. 线路号后加"路"字
3. 上车点后加"上车"，下车站后加"下车"
4. 物品描述保留原文语义不增不减

【参考范例】
输入：5月18日 60路 16:03 丁家村下车 崇贤新城总站 黑色折叠伞
输出：60路，5月18日16:03分左右丁家村上车-崇贤新城总站下车，遗失：黑色折叠伞。

输入：137路 19:46 汤家桥东-滨康小区 丢失蓝牙耳机仓 紫色保护壳
输出：137路，19:46汤家桥东上车-滨康小区下车，遗失：蓝牙耳机仓紫色保护壳。

**只输出一行话术，不要任何解释、不要markdown标记**'''
    },
    'refund': {
        'name': '刷卡退费',
        'prompt': '''你是杭州公交热线话术助手。请严格按以下格式组织碎片信息。

【模板格式】
{线路}路，{日期}{时间}{站点}上车，{扣费原因}，卡号：{卡号}，{姓名}。要求退款。

【关键规则】
1. **日期**：如果碎片中包含日期，必须提取并放在时间前面。没有则不写。
2. 线路号后加"路"字
3. 卡号保留完整数字

【参考范例】
输入：5月12日 505路 9:40 密度桥上车 一码通重复扣费 3100700505050588 程瑾
输出：505路，5月12日9:40左右密度桥上车，上车刷一码通重复扣费，卡号：3100700505050588，程瑾。要求退款。

**只输出一行话术，不要任何解释、不要markdown标记**'''
    },
    'custom': {
        'name': '定制公交',
        'prompt': '''你是杭州公交热线话术助手。请严格按以下格式组织碎片信息。

【模板格式】
定制公交：{活动日期}，{人数}人左右，{时间}{起点}—{终点}，{往返/单程}。联系人：{姓名}，{电话}。

【关键规则】
1. 活动日期从碎片中提取
2. 起终点用"—"连接

【参考范例】
输入：6月6号7号 500人 早上7点 石祥西路欧亚美国际大酒店到浙大体育馆 往返 杨先生 13738096272
输出：定制公交：6月6日-7日，500人左右，7:00石祥西路859号欧亚美国际大酒店—浙大体育馆，往返。联系人：杨先生，13738096272。

**只输出一行话术，不要任何解释、不要markdown标记**'''
    },
    'complaint': {
        'name': '投诉建议',
        'prompt': '''你是杭州公交热线话术助手。请严格按以下格式组织碎片信息。

【模板格式】
{线路}路，车号{车号}，{日期}{时间}左右在{地点}，{投诉内容}。{诉求}。备注：{备注信息}。

【关键规则】
1. **日期**：如果碎片中包含日期（如"5月18日""今天""昨天"），必须提取放在时间前面。没有则不写。
2. 线路号后加"路"字
3. 车号格式如"浙A02977D"，保留完整
4. 投诉内容保留原文语义，组织条理清晰
5. 如涉及安保部/安全科等，备注中注明"需安保部核查处理"
6. 诉求明确化（如"要求调查处理司机行为""要求核实违规行为"）

【参考范例】
输入：1602路 浙A02977D 今天11:38 机场路一巷 司机车速很快斑马线未礼让行人险些碰撞 外卖人员 要求调查处理 备注安保部核查
输出：1602路，车号浙A02977D，5月22日11:38分左右在机场路一巷，行驶时车速较快斑马线未礼让行人导致险些碰撞（当事人为外卖人员）。要求调查处理司机行为。备注：该情况需安保部核查处理。

**只输出一行话术，不要任何解释、不要markdown标记**'''
    }
}

ORGANIZE_HTML = r'''<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>话术智能组织</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:PingFang SC,Microsoft YaHei,sans-serif;background:#0f1923;color:#e0e0e0;min-height:100vh;display:flex;justify-content:center;padding:16px}
.container{max-width:860px;width:100%}
h1{text-align:center;font-size:20px;margin-bottom:8px;letter-spacing:2px;color:#e8e8e8}
.status{text-align:center;font-size:12px;color:#5a7a8e;margin-bottom:16px}
.status .ok{color:#4ade80}.status .err{color:#f87171}
.row2{display:flex;gap:12px;margin-bottom:12px}
.left{flex:3;min-width:0}.right{flex:2;min-width:0}
.tpl-tabs{display:flex;gap:8px;margin-bottom:12px}
.tab{flex:1;padding:10px;background:#1a2733;border:2px solid #243447;border-radius:8px;text-align:center;cursor:pointer;transition:.15s;font-size:14px}
.tab:hover{border-color:#4a6a5a}.tab.active{border-color:#2d7d46;background:#1a2e24}
.tab .n{font-weight:bold;display:block}
textarea{width:100%;min-height:140px;background:#111d26;border:1px solid #243447;border-radius:10px;color:#d0d0d0;padding:14px;font-size:14px;line-height:1.8;resize:vertical;outline:none;font-family:inherit}
textarea:focus{border-color:#2d7d46}
.btn-row{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.btn{padding:11px 24px;border:none;border-radius:8px;font-size:14px;cursor:pointer;transition:.15s;white-space:nowrap;font-weight:bold}
.btn-go{background:#2d7d46;color:#fff;flex:1;font-size:16px}
.btn-go:hover{background:#256b3a}.btn-go:disabled{opacity:.4;cursor:not-allowed}
.btn-copy{background:#2d5a7d;color:#fff}.btn-copy:hover{background:#234b6b}
.btn-outline{background:transparent;border:1px solid #3d5567;color:#8aa8b8}.btn-outline:hover{background:#1a2a38}
.result-panel{background:#1a2733;border-radius:10px;overflow:hidden;display:flex;flex-direction:column;min-height:200px}
.result-header{padding:10px 14px;border-bottom:1px solid #243447;display:flex;justify-content:space-between;align-items:center}
.result-header .label{font-size:13px;color:#4ade80;font-weight:bold}
.result-body{flex:1;padding:14px;font-size:15px;line-height:1.9;color:#e0e0e0;white-space:pre-wrap;min-height:80px;overflow-y:auto}
.result-body.empty{color:#4a6a7e;font-style:italic}
.toast{position:fixed;top:20px;left:50%;transform:translateX(-50%);background:#2d7d46;color:#fff;padding:10px 24px;border-radius:8px;font-size:14px;z-index:1000;opacity:0;transition:opacity .2s;pointer-events:none}
.toast.show{opacity:1}
@media(max-width:700px){.row2{flex-direction:column}}
</style></head><body>
<div class="container">
<h1>话术智能组织</h1>
<div class="status" id="apiStatus">API: 检测中...</div>
<div class="tpl-tabs">
<div class="tab active" data-tpl="lost" onclick="switchTpl('lost',this)"><span class="n">🎒 失物招领</span></div>
<div class="tab" data-tpl="refund" onclick="switchTpl('refund',this)"><span class="n">💳 刷卡退费</span></div>
<div class="tab" data-tpl="custom" onclick="switchTpl('custom',this)"><span class="n">🚌 定制公交</span></div>
<div class="tab" data-tpl="complaint" onclick="switchTpl('complaint',this)"><span class="n">⚠️ 投诉建议</span></div>
</div>
<div class="row2">
<div class="left">
<textarea id="input" placeholder="随便写，口语也行：&#10;60路 黑色折叠伞 16:03 丁家村下车 崇贤新城总站&#10;137路 19:46 汤家桥东-滨康小区 丢蓝牙耳机仓 紫色保护壳"></textarea>
<div class="btn-row">
<button class="btn btn-go" id="btnGo" onclick="organize()">⚡ 智能组织</button>
<button class="btn btn-copy" onclick="copyResult()">复制</button>
<button class="btn btn-outline" onclick="clearAll()">清空</button>
</div>
</div>
<div class="right">
<div class="result-panel">
<div class="result-header"><span class="label">📝 AI 组织结果</span></div>
<div class="result-body empty" id="output">等待输入...</div>
</div>
</div>
</div>
</div>
<div class="toast" id="toast"></div>
<script>
var currentTpl='lost',apiReady=false;
fetch('/api/status').then(r=>r.json()).then(d=>{
  apiReady=d.ok;
  document.getElementById('apiStatus').innerHTML=apiReady?'<span class="ok">● AI已就绪</span>':'<span class="err">● 请设置 DEEPSEEK_API_KEY 环境变量后重启</span>';
}).catch(function(){document.getElementById('apiStatus').innerHTML='<span class="err">● 服务未连接</span>'});
function switchTpl(t,el){currentTpl=t;document.querySelectorAll('.tab').forEach(function(x){x.classList.remove('active')});el.classList.add('active')}
function organize(){
  var raw=document.getElementById('input').value.trim();
  if(!raw){showToast('请先输入碎片信息');return}
  if(!apiReady){showToast('API未就绪');return}
  var btn=document.getElementById('btnGo');
  btn.disabled=true;btn.textContent='⏳ AI组织中...';
  document.getElementById('output').innerHTML='<span style="color:#5a7a8e">⏳ AI正在理解语义...</span>';
  document.getElementById('output').classList.remove('empty');
  fetch('/api/organize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:raw,template:currentTpl})})
  .then(function(r){return r.json()}).then(function(d){
    document.getElementById('output').textContent=d.result||d.error||'无结果';
    document.getElementById('output').classList.remove('empty');
    btn.disabled=false;btn.textContent='⚡ 智能组织';
  }).catch(function(e){
    document.getElementById('output').textContent='请求失败: '+e;
    btn.disabled=false;btn.textContent='⚡ 智能组织';
  });
}
function copyResult(){
  var t=document.getElementById('output').textContent;
  if(!t.trim()||t.indexOf('等待')==0||t.indexOf('⏳')==0){showToast('没有可复制的内容');return}
  navigator.clipboard.writeText(t).then(function(){showToast('已复制')});
}
function clearAll(){document.getElementById('input').value='';document.getElementById('output').textContent='等待输入...';document.getElementById('output').classList.add('empty')}
function showToast(msg){var t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');clearTimeout(t._t);t._t=setTimeout(function(){t.classList.remove('show')},1800)}
</script></body></html>'''

NAV_HTML = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>工具站</title>
<style>body{font-family:PingFang SC,sans-serif;background:#0f1923;color:#e0e0e0;display:flex;justify-content:center;padding:40px}
a{display:block;padding:16px 24px;margin:8px 0;background:#1a2733;border:1px solid #243447;border-radius:8px;color:#4ade80;text-decoration:none;font-size:16px}
a:hover{background:#1e2e3c}</style></head><body><div>
<h2>🛠 桌面工具站</h2>
<a href="/dispatch_selfcontained.html">📍 派工查询</a>
<a href="/工单备注替换工具.html">📝 工单备注替换</a>
<a href="/话术组织.html">💬 话术智能组织</a>
<a href="/公交综合查询系统.html">🔍 公交综合查询</a>
</div></body></html>'''


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DESKTOP, **kwargs)

    def do_GET(self):
        path = urllib.parse.unquote(self.path.split('?')[0])

        if path == '/' or path == '/index.html':
            self._html(NAV_HTML)
        elif path == '/话术组织.html':
            self._html(ORGANIZE_HTML)
        elif path == '/api/status':
            self._json({'ok': bool(API_KEY)})
        elif path in ALLOW:
            super().do_GET()
        else:
            self.send_error(404, f'Forbidden: {path}')

    def do_POST(self):
        path = urllib.parse.unquote(self.path.split('?')[0])
        if path == '/api/organize':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            data = json.loads(body)
            text = data.get('text', '')
            tpl = data.get('template', 'lost')
            result = self._call_ai(text, tpl)
            self._json({'result': result})
        elif path == '/api/analyze':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            data = json.loads(body)
            query = data.get('query', '')
            context = data.get('context', '')
            result = self._call_ai_analyze(query, context)
            self._json({'result': result})
        else:
            self.send_error(404)

    def _call_ai(self, text, tpl_name):
        if not API_KEY:
            return '请先设置 DEEPSEEK_API_KEY 环境变量'
        tpl = TEMPLATES.get(tpl_name, TEMPLATES['lost'])
        try:
            import requests
            r = requests.post(API_URL, headers={
                'Authorization': f'Bearer {API_KEY}',
                'Content-Type': 'application/json'
            }, json={
                'model': 'deepseek-chat',
                'messages': [
                    {'role': 'system', 'content': tpl['prompt']},
                    {'role': 'user', 'content': f'【待组织的碎片信息】\n{text}'}
                ],
                'temperature': 0.3,
                'max_tokens': 500
            }, timeout=30)
            if r.status_code == 200:
                return r.json()['choices'][0]['message']['content'].strip()
            return f'API错误 ({r.status_code})'
        except Exception as e:
            return f'请求失败: {str(e)}'

    def _call_ai_analyze(self, query, context):
        if not API_KEY:
            return '请先设置 DEEPSEEK_API_KEY 环境变量'
        context = context[:4000]
        try:
            import requests
            r = requests.post(API_URL, headers={
                'Authorization': f'Bearer {API_KEY}',
                'Content-Type': 'application/json'
            }, json={
                'model': 'deepseek-chat',
                'messages': [
                    {'role': 'system', 'content': '你是杭州公交业务分析专家。根据提供的文档内容，针对用户查询的关键词，生成分析摘要。要求：1.提取关键信息（线路变更、站点调整、施工影响、公司安排等）2.按重要程度排序 3.控制在300字以内 4.用简洁中文列表格式'},
                    {'role': 'user', 'content': f'查询关键词：{query}\n相关文档：\n{context}\n\n生成分析摘要：'}
                ],
                'temperature': 0.3, 'max_tokens': 600
            }, timeout=30)
            if r.status_code == 200:
                return r.json()['choices'][0]['message']['content'].strip()
            return f'API错误({r.status_code})'
        except Exception as e:
            return f'请求失败: {str(e)}'

    def _html(self, content):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

    def _json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    import socketserver
    class ReusableServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        allow_reuse_address = True
        daemon_threads = True

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.254.254.254', 1))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = '你的IP'

    if not API_KEY:
        print('⚠ 未设置 DEEPSEEK_API_KEY，话术组织将不可用（其他工具正常）')
        print('  设置: $env:DEEPSEEK_API_KEY="你的key"')
    else:
        print('✅ AI 已就绪')

    print(f'\n🚀 桌面工具站已启动 (端口 {PORT})')
    print(f'   本机: http://localhost:{PORT}')
    print(f'   局域网: http://{local_ip}:{PORT}')
    print(f'   ngrok: ngrok http {PORT}')
    print(f'🛑 Ctrl+C 停止\n')

    server = ReusableServer(('0.0.0.0', PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务已停止')
        server.server_close()
