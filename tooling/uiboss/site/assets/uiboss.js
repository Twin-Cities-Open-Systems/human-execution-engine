(function(){
  function setTheme(t){
    document.documentElement.setAttribute('data-theme', t);
    try{ localStorage.setItem('uiboss.theme', t); }catch(e){}
  }
  function initTheme(){
    var t=null;
    try{ t=localStorage.getItem('uiboss.theme'); }catch(e){}
    if(!t) t='dark';
    setTheme(t);
  }
  function initToggle(){
    var b=document.getElementById('themeToggle');
    if(!b) return;
    b.addEventListener('click', function(){
      var cur=document.documentElement.getAttribute('data-theme')||'dark';
      setTheme(cur==='dark'?'light':'dark');
    });
  }
  function markActive(){
    var p=(location.pathname||"/");
    if(p==="/index.html") p="/";
    var key="home";
    if(p.startsWith("/runs")) key="runs";
    else if(p.startsWith("/repos")) key="repos";
    else if(p.startsWith("/fs")) key="fs";
    else if(p.startsWith("/view")) key="view";

    document.querySelectorAll('[data-tab]').forEach(function(a){
      if(a.getAttribute('data-tab')===key) a.classList.add('active');
      else a.classList.remove('active');
    });
  }
  document.addEventListener('DOMContentLoaded', function(){
    initTheme(); initToggle(); markActive();
  });
})();
