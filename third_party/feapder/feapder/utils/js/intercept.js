!function(t,e){for(var n in e)t[n]=e[n]}(window,function(t){function e(r){if(n[r])return n[r].exports;var o=n[r]={i:r,l:!1,exports:{}};return t[r].call(o.exports,o,o.exports,e),o.l=!0,o.exports}var n={};return e.m=t,e.c=n,e.i=function(t){return t},e.d=function(t,n,r){e.o(t,n)||Object.defineProperty(t,n,{configurable:!1,enumerable:!0,get:r})},e.n=function(t){var n=t&&t.__esModule?function(){return t.default}:function(){return t};return e.d(n,"a",n),n},e.o=function(t,e){return Object.prototype.hasOwnProperty.call(t,e)},e.p="",e(e.s=3)}([function(t,e,n){"use strict";function r(t,e){var n={};for(var r in t)n[r]=t[r];return n.target=n.currentTarget=e,n}function o(t){function e(e){return function(){var n=this.hasOwnProperty(e+"_")?this[e+"_"]:this.xhr[e],r=(t[e]||{}).getter;return r&&r(n,this)||n}}function n(e){return function(n){var o=this.xhr,i=this,u=t[e];if("on"===e.substring(0,2))i[e+"_"]=n,o[e]=function(u){u=r(u,i),t[e]&&t[e].call(i,o,u)||n.call(i,u)};else{var s=(u||{}).setter;n=s&&s(n,i)||n,this[e+"_"]=n;try{o[e]=n}catch(t){}}}}function o(e){return function(){var n=[].slice.call(arguments);if(t[e]){var r=t[e].call(this,n,this.xhr);if(r)return r}return this.xhr[e].apply(this.xhr,n)}}return window[s]=window[s]||XMLHttpRequest,XMLHttpRequest=function(){var t=new window[s];for(var r in t){var i="";try{i=u(t[r])}catch(t){}"function"===i?this[r]=o(r):Object.defineProperty(this,r,{get:e(r),set:n(r),enumerable:!0})}var a=this;t.getProxy=function(){return a},this.xhr=t},window[s]}function i(){window[s]&&(XMLHttpRequest=window[s]),window[s]=void 0}Object.defineProperty(e,"__esModule",{value:!0});var u="function"==typeof Symbol&&"symbol"==typeof Symbol.iterator?function(t){return typeof t}:function(t){return t&&"function"==typeof Symbol&&t.constructor===Symbol&&t!==Symbol.prototype?"symbol":typeof t};e.configEvent=r,e.hook=o,e.unHook=i;var s="_rxhr"},function(t,e,n){"use strict";function r(t){if(h)throw"Proxy already exists";return h=new f(t)}function o(){h=null,(0,d.unHook)()}function i(t){return t.replace(/^\s+|\s+$/g,"")}function u(t){return t.watcher||(t.watcher=document.createElement("a"))}function s(t,e){var n=t.getProxy(),r="on"+e+"_",o=(0,d.configEvent)({type:e},n);n[r]&&n[r](o);var i;"function"==typeof Event?i=new Event(e,{bubbles:!1}):(i=document.createEvent("Event"),i.initEvent(e,!1,!0)),u(t).dispatchEvent(i)}function a(t){this.xhr=t,this.xhrProxy=t.getProxy()}function c(t){function e(t){a.call(this,t)}return e[b]=Object.create(a[b]),e[b].next=t,e}function f(t){function e(t,e){var n=new P(t);if(!f)return n.resolve();var r={response:e.response,status:e.status,statusText:e.statusText,config:t.config,headers:t.resHeader||t.getAllResponseHeaders().split("\r\n").reduce(function(t,e){if(""===e)return t;var n=e.split(":");return t[n.shift()]=i(n.join(":")),t},{})};f(r,n)}function n(t,e,n){var r=new H(t),o={config:t.config,error:n};h?h(o,r):r.next(o)}function r(){return!0}function o(t,e){return n(t,this,e),!0}function a(t,n){return 4===t.readyState&&0!==t.status?e(t,n):4!==t.readyState&&s(t,w),!0}var c=t.onRequest,f=t.onResponse,h=t.onError;return(0,d.hook)({onload:r,onloadend:r,onerror:o,ontimeout:o,onabort:o,onreadystatechange:function(t){return a(t,this)},open:function(t,e){var r=this,o=e.config={headers:{}};o.method=t[0],o.url=t[1],o.async=t[2],o.user=t[3],o.password=t[4],o.xhr=e;var i="on"+w;e[i]||(e[i]=function(){return a(e,r)});var u=function(t){n(e,r,(0,d.configEvent)(t,r))};if([x,y,g].forEach(function(t){var n="on"+t;e[n]||(e[n]=u)}),c)return!0},send:function(t,e){var n=e.config;if(n.withCredentials=e.withCredentials,n.body=t[0],c){var r=function(){c(n,new m(e))};return!1===n.async?r():setTimeout(r),!0}},setRequestHeader:function(t,e){return e.config.headers[t[0].toLowerCase()]=t[1],!0},addEventListener:function(t,e){var n=this;if(-1!==l.indexOf(t[0])){var r=t[1];return u(e).addEventListener(t[0],function(e){var o=(0,d.configEvent)(e,n);o.type=t[0],o.isTrusted=!0,r.call(n,o)}),!0}},getAllResponseHeaders:function(t,e){var n=e.resHeader;if(n){var r="";for(var o in n)r+=o+": "+n[o]+"\r\n";return r}},getResponseHeader:function(t,e){var n=e.resHeader;if(n)return n[(t[0]||"").toLowerCase()]}})}Object.defineProperty(e,"__esModule",{value:!0}),e.proxy=r,e.unProxy=o;var h,d=n(0),l=["load","loadend","timeout","error","readystatechange","abort"],v=l[0],p=l[1],y=l[2],x=l[3],w=l[4],g=l[5],b="prototype";a[b]=Object.create({resolve:function(t){var e=this.xhrProxy,n=this.xhr;e.readyState=4,n.resHeader=t.headers,e.response=e.responseText=t.response,e.statusText=t.statusText,e.status=t.status,s(n,w),s(n,v),s(n,p)},reject:function(t){this.xhrProxy.status=0,s(this.xhr,t.type),s(this.xhr,p)}});var m=c(function(t){var e=this.xhr;t=t||e.config,e.withCredentials=t.withCredentials,e.open(t.method,t.url,!1!==t.async,t.user,t.password);for(var n in t.headers)e.setRequestHeader(n,t.headers[n]);e.send(t.body)}),P=c(function(t){this.resolve(t)}),H=c(function(t){this.reject(t)})},,function(t,e,n){"use strict";Object.defineProperty(e,"__esModule",{value:!0}),e.ah=void 0;var r=n(0),o=n(1);e.ah={proxy:o.proxy,unProxy:o.unProxy,hook:r.hook,unHook:r.unHook}}]));

// 存储数据
window.__ajaxData = {}
// 拦截规则
window.__urlRegexes = []

ah.proxy({
    onRequest: (config,handler)=>{
        handler.next(config);
    }
    ,
    onError: (err,handler)=>{
        handler.next(err)
    }
    ,
    onResponse: (response,handler)=>{
        var url = response.config.url;
        if (window.__urlRegexes.length > 0) {
            for (const regex of window.__urlRegexes) {
                var re = new RegExp(regex, "g");
                if (re.exec(url)) {
                    window.__ajaxData[regex] = {
                        request: {
                            'url': response.config.xhr.config.url,
                            'data': response.config.xhr.config.body,
                            'headers': response.config.xhr.config.headers
                        },
                        response: {
                            'url': response.config.url,
                            'headers': response.headers,
                            'content': response.response,
                            'status_code': response.status
                        }
                    };
                }
            }
        }
        handler.next(response)
    }
})
