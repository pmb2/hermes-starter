// ==UserScript==
// @name         PIM Full Extractor v2
// @namespace    http://pim.local/
// @version      2.0
// @description  Extract ChatGPT & Grok conversation IDs AND content via browser API
// @match        https://chatgpt.com/*
// @match        https://grok.com/*
// @grant        GM_xmlhttpRequest
// @run-at       document-idle
// ==/UserScript==

(function() {
  "use strict";
  if (window.__PIM_DONE) return;
  window.__PIM_DONE = true;

  var API = "http://127.0.0.1:8897/ingest";
  var isChat = location.hostname.indexOf("chatgpt") !== -1;
  var isGrok = location.hostname.indexOf("grok") !== -1;
  if (!isChat && !isGrok) return;

  var checkTimer = setInterval(function() {
    var links = document.querySelectorAll(isChat ? 'a[href*="/c/"]' : 'a[href*="/chat/"]');
    if (links.length > 0 || window.__PIM_TRIES > 20) {
      clearInterval(checkTimer);
      doExtract();
    }
    window.__PIM_TRIES = (window.__PIM_TRIES || 0) + 1;
  }, 1000);

  function doExtract() {
    var SEL = isChat ? 'a[href*="/c/"]' : 'a[href*="/chat/"]';
    var RE = isChat ? /\/c\/([a-f0-9-]+)/ : /\/chat\/([a-f0-9-]+)/;
    var convs = [];
    var seen = {};
    document.querySelectorAll(SEL).forEach(function(a) {
      var m = a.href.match(RE);
      if (m && !seen[m[1]]) { seen[m[1]] = true; convs.push({id:m[1],title:(a.textContent||"").trim()||"Untitled",url:a.href}); }
    });
    if (convs.length === 0) { console.log("[PIM] No convos"); return; }
    console.log("[PIM] Found " + convs.length + " convos");
    var done = 0;
    convs.forEach(function(c) {
      var apiUrl = isChat ? "https://chatgpt.com/backend-api/conversation/" + c.id : "https://grok.com/rest/app-chat/conversations/" + c.id;
      GM_xmlhttpRequest({
        method: "GET", url: apiUrl,
        headers: { "Accept": "application/json", "Referer": isChat ? "https://chatgpt.com/" : "https://grok.com/" },
        onload: function(resp) {
          if (resp.status === 200) {
            try {
              var data = JSON.parse(resp.responseText);
              var msgs = [];
              if (isChat && data.mapping) {
                Object.keys(data.mapping).forEach(function(key) {
                  var msg = data.mapping[key].message;
                  if (msg && msg.content) {
                    msgs.push({role: (msg.author&&msg.author.role)||"unknown", content: typeof msg.content==="string"?msg.content:(msg.content.parts||[]).join("\n")});
                  }
                });
              } else if (data.messages || (data.conversation&&data.conversation.messages)) {
                var raw = data.messages || data.conversation.messages || [];
                raw.forEach(function(m) { msgs.push({role: m.role||"unknown", content: m.content||(m.parts||[]).join("\n")||""}); });
              }
              c.messages = msgs;
              c.content_fetched = true;
              console.log("[PIM] " + msgs.length + " msgs: " + (c.title||"").substring(0,40));
            } catch(e) { console.log("[PIM] Parse fail " + c.id); }
          } else { console.log("[PIM] API " + resp.status + " " + c.id); }
          done++; if (done === convs.length) sendAll(convs);
        },
        onerror: function() { done++; if (done === convs.length) sendAll(convs); }
      });
    });
  }

  function sendAll(convs) {
    GM_xmlhttpRequest({
      method: "POST", url: API, headers: {"Content-Type":"application/json"},
      data: JSON.stringify({source:isChat?"chatgpt":"grok", conversations: convs}),
      onload: function(r) { console.log("[PIM] Server:", r.responseText);
        var wc = convs.filter(function(c){return c.content_fetched}).length;
        alert("[PIM] " + convs.length + " convos (" + wc + " with content)"); }
    });
  }
})();
