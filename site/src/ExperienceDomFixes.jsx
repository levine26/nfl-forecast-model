import { useEffect } from 'react'

export default function ExperienceDomFixes() {
  useEffect(()=>{
    const apply=()=>{
      document.querySelectorAll('.ss-exp-top-signals button,.ss-exp-board-rows button,.ss-exp-mobile-board button').forEach(button=>{
        button.setAttribute('data-game-open','')
        if (!button.getAttribute('aria-label')) button.setAttribute('aria-label',button.textContent?.replace(/\s+/g,' ').trim()||'Open matchup')
      })
      document.querySelectorAll('.ss-mobile-nav button small').forEach(label=>{if(label.textContent==='Power') label.textContent='Rankings'})
      const receipt=document.getElementById('ss-exp-receipt')
      if (receipt && window.matchMedia('(max-width: 768px)').matches) {
        const mobileHeader=document.querySelector('.ss-mobile-header')
        if (mobileHeader && receipt.previousElementSibling!==mobileHeader) mobileHeader.insertAdjacentElement('afterend',receipt)
      }
    }
    apply()
    const observer=new MutationObserver(apply)
    observer.observe(document.getElementById('root')||document.body,{childList:true,subtree:true})
    const onResize=()=>apply()
    window.addEventListener('resize',onResize)
    return()=>{observer.disconnect();window.removeEventListener('resize',onResize)}
  },[])
  return null
}
