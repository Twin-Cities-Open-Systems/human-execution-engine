(function(){
  function qs(k){ var u=new URL(window.location.href); return u.searchParams.get(k)||""; }
  function setqs(k,v){ var u=new URL(window.location.href); if(v===null) u.searchParams.delete(k); else u.searchParams.set(k,v); window.location.href=u.toString(); }
  function esc(s){ return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

  function normPath(p){
    p=(p||"").trim();
    if(!p) return "";
    if(p.indexOf("..")!==-1) return "";
    if(p[0]==="/") return p;
    if(/^runs\//.test(p) || /^repos\//.test(p) || /^assets\//.test(p) || /^fs\//.test(p) || /^view\//.test(p)) return "/"+p;
    return "/runs/"+p;
  }

  function baseDir(path){
    var i = path.lastIndexOf("/");
    if(i<=0) return "/";
    return path.slice(0,i+1);
  }
  function resolveUrl(b,u){
    u=(u||"").trim();
    if(!u) return u;
    if(/^(https?:|data:)/i.test(u)) return u;
    if(u[0]==="/") return u;
    return b + u;
  }

  function mdToHtml(md, b){
    md=(md||"").replace(/\r\n/g,"\n");
    var lines=md.split("\n");
    var out="";
    var inCode=false;
    var codeLang="";

    // mermaid fences => <div class="mermaid">...</div>
    for(var i=0;i<lines.length;i++){
      var l=lines[i];

      var fence = l.match(/^```(\w+)?\s*$/);
      if(fence){
        if(!inCode){
          inCode=true; codeLang=(fence[1]||"").toLowerCase();
          if(codeLang==="mermaid"){ out += "<div class=\"mermaid\">\n"; }
          else { out += "<pre><code>"; }
        }else{
          if(codeLang==="mermaid"){ out += "\n</div>\n"; }
          else { out += "</code></pre>\n"; }
          inCode=false; codeLang="";
        }
        continue;
      }

      if(inCode){
        if(codeLang==="mermaid"){ out += l + "\n"; }
        else { out += esc(l) + "\n"; }
        continue;
      }

      var h=l.match(/^(#{1,6})\s+(.*)$/);
      if(h){ out += "<h"+h[1].length+">"+esc(h[2])+"</h"+h[1].length+">\n"; continue; }
      if(l.trim()===""){ out += "<div style=\"height:8px\"></div>\n"; continue; }

      // images
      l = l.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, function(_,alt,u){
        var uu = resolveUrl(b,u||"");
        return '<img class="mdimg" src="'+esc(uu)+'" alt="'+esc(alt||"")+'">';
      });

      // links (route local non-html through viewer)
      l = l.replace(/\[([^\]]+)\]\(([^)]+)\)/g, function(_,txt,u){
        var uu = resolveUrl(b,u||"");
        if(uu[0]==="/" && !/\.html?$/i.test(uu)){
          return '<a href="/view/?p='+encodeURIComponent(uu)+'">'+esc(txt)+'</a>';
        }
        return '<a href="'+esc(uu)+'" rel="noreferrer">'+esc(txt)+'</a>';
      });

      // inline code
      var t = esc(l).replace(/`([^`]+)`/g, function(_,x){ return "<code>"+esc(x)+"</code>"; });

      // allowlist unescape for injected tags
      t = t
        .replace(/&lt;img /g,"<img ")
        .replace(/&lt;a /g,"<a ")
        .replace(/&lt;\/a&gt;/g,"</a>")
        .replace(/&gt;/g,">")
        .replace(/&lt;\/code&gt;/g,"</code>")
        .replace(/&lt;code&gt;/g,"<code>");

      out += "<p>"+t+"</p>\n";
    }
    if(inCode){
      out += (codeLang==="mermaid") ? "\n</div>\n" : "</code></pre>\n";
    }
    return out;
  }

  function addCopy(pre){
    if(!pre || pre.querySelector(".copybtn")) return;
    var btn=document.createElement("button");
    btn.className="copybtn"; btn.type="button"; btn.textContent="copy";
    btn.addEventListener("click", function(){
      var code=pre.querySelector("code");
      var txt=code ? code.textContent : pre.textContent;
      navigator.clipboard.writeText(txt).then(function(){
        btn.textContent="copied"; setTimeout(function(){btn.textContent="copy";}, 900);
      }, function(){
        btn.textContent="nope"; setTimeout(function(){btn.textContent="copy";}, 900);
      });
    });
    pre.appendChild(btn);
  }

  function htmlOriginRewrite(html){
    // Heuristic: if it looks like a BLS capture, rewrite root-relative assets to https://www.bls.gov
    var looksBls = /bls\.gov|bls_/i.test(html) || /\/(javascripts|stylesheets|images)\//i.test(html);
    if(looksBls){
      html = html
        .replace(/(src|href)=["']\/(javascripts|stylesheets|images)\//gi, '$1="https://www.bls.gov/$2/')
        .replace(/(src|href)=["']\/favicon\.ico/gi, '$1="https://www.bls.gov/favicon.ico');
    }

    // Our earlier missing bootstrap paths: rewrite to CDN
    html = html
      .replace(/(["'])\/assets\/bootstrap\/latest\/bootstrap\.min\.js\1/gi, '$1https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.min.js$1')
      .replace(/(["'])\/assets\/bootstrap\/latest\/popper\.min\.js\1/gi, '$1https://cdn.jsdelivr.net/npm/@popperjs/core@2.11.8/dist/umd/popper.min.js$1')
      .replace(/(["'])\/javascripts\/jquery-latest\.js\1/gi, '$1https://code.jquery.com/jquery-3.7.1.min.js$1');

    return html;
  }

  function tryEnhanceMd(container){
    // Mermaid
    try{
      if(window.mermaid){
        window.mermaid.initialize({ startOnLoad:false, securityLevel:"strict" });
        window.mermaid.run({ querySelector: ".mermaid" });
      }
    }catch(e){}

    // KaTeX auto-render
    try{
      if(window.renderMathInElement){
        window.renderMathInElement(container, {
          delimiters: [
            {left: "$$", right: "$$", display: true},
            {left: "$", right: "$", display: false}
          ],
          throwOnError: false
        });
      }
    }catch(e){}
  }

  async function main(){
    var rawp=qs("p");
    var p=normPath(rawp);
    var mode=(qs("mode")||"").toLowerCase(); // render | code | unsafe
    var title=document.getElementById("title");
    var meta=document.getElementById("meta");
    var content=document.getElementById("content");

    var openRaw=document.getElementById("openRaw");
    var modeRender=document.getElementById("modeRender");
    var modeCode=document.getElementById("modeCode");
    var modeUnsafe=document.getElementById("modeUnsafe");

    if(!p){
      title.textContent="View (missing/invalid ?p=)";
      meta.textContent="Example: /view/?p=/fs/mounts/git-dot-hee/evidence/.../E70-hee-shapes-mermaid.md";
      return;
    }

    title.textContent=p;
    if(openRaw) openRaw.href=p;

    if(modeRender) modeRender.addEventListener("click", function(e){ e.preventDefault(); setqs("mode","render"); });
    if(modeCode) modeCode.addEventListener("click", function(e){ e.preventDefault(); setqs("mode","code"); });
    if(modeUnsafe) modeUnsafe.addEventListener("click", function(e){ e.preventDefault(); setqs("mode","unsafe"); });

    var ext=(p.split(".").pop()||"").toLowerCase();
    if(!mode){
      if(ext==="html" || ext==="htm") mode="render";
      else if(ext==="md" || ext==="markdown") mode="render";
      else mode="code";
    }

    // HTML render via srcdoc + optional unsafe scripts + origin rewrite
    if((ext==="html" || ext==="htm") && (mode==="render" || mode==="unsafe")){
      meta.textContent="mode="+mode+" (srcdoc) · "+p;
      var res=await fetch(p,{cache:"no-store"});
      var html=await res.text();
      html = htmlOriginRewrite(html);

      var ifr=document.createElement("iframe");
      ifr.className="viewer";
      if(mode==="unsafe") ifr.setAttribute("sandbox","allow-scripts allow-same-origin");
      else ifr.setAttribute("sandbox","");
      ifr.srcdoc = html;

      content.innerHTML="";
      content.appendChild(ifr);
      return;
    }

    // image preview
    if(/^(png|jpg|jpeg|gif|webp|svg)$/.test(ext)){
      meta.textContent="image preview · "+p;
      var img=document.createElement("img");
      img.src=p;
      img.className="mdimg";
      content.innerHTML="";
      content.appendChild(img);
      return;
    }

    // fetch + render code/md
    var res2=await fetch(p,{cache:"no-store"});
    meta.textContent="HTTP "+res2.status+" · "+(res2.headers.get("content-type")||"(no content-type)")+" · mode="+mode;
    var txt=await res2.text();

    if(!res2.ok){
      content.innerHTML="<pre><code>"+esc(txt)+"</code></pre>";
      addCopy(content.querySelector("pre"));
      return;
    }

    if((ext==="md" || ext==="markdown") && mode==="render"){
      content.innerHTML = mdToHtml(txt, baseDir(p));
      tryEnhanceMd(content);
      return;
    }

    var pre=document.createElement("pre"), code=document.createElement("code");
    code.textContent=txt; pre.appendChild(code);
    content.innerHTML=""; content.appendChild(pre);
    addCopy(pre);
  }

  document.addEventListener("DOMContentLoaded", function(){
    main().catch(function(e){
      var content=document.getElementById("content");
      content.innerHTML="<pre><code>"+esc(String(e))+"</code></pre>";
    });
  });
})();
