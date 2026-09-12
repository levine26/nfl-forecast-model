import { useEffect } from 'react'

/**
 * Small DOM-compatibility bridge for presentation-only layers that coexist
 * with the canonical AppSignal tree. This component intentionally registers
 * before ExperienceLayer so it can normalize legacy hooks before later
 * presentation observers see them.
 */
export default function ExperienceDomFixes() {
  useEffect(()=>{
    const apply=()=>{
      document.querySelectorAll('.ss-exp-top-signals button,.ss-exp-board-rows button,.ss-exp-mobile-board button').forEach(button=>{
        button.setAttribute('data-game-open','')
        if (!button.getAttribute('aria-label')) button.setAttribute('aria-label',button.textContent?.replace(/\s+/g,' ').trim()||'Open matchup')
      })

      document.querySelectorAll('.ss-mobile-nav button small').forEach(label=>{
        if (label.textContent==='Power') label.textContent='Rankings'
      })

      // PresentationTextPass historically targets .ss-how-link and writes its
      // textContent. Normalize once, then move the legacy class out of that
      // observer's query so the write cannot create a self-sustaining
      // childList MutationObserver loop on matchup routes.
      document.querySelectorAll('.ss-how-link').forEach(button=>{
        if (button.textContent!=='How LevLine Works →') button.textContent='How LevLine Works →'
        button.classList.remove('ss-how-link')
        button.classList.add('ss-how-link-v2')
      })

      const receiptRoute=window.location.hash.startsWith('#/receipt/')
      if (receiptRoute) {
        const desktop=[...document.querySelectorAll('.ss-desktop-nav button')]
        desktop.forEach(button=>button.classList.remove('active'))
        desktop.find(button=>button.textContent==='History')?.classList.add('active')
        const mobile=[...document.querySelectorAll('.ss-mobile-nav button')]
        mobile.forEach(button=>button.classList.remove('active'))
        mobile.find(button=>button.textContent?.includes('History'))?.classList.add('active')
      }

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
    const onHash=()=>apply()
    window.addEventListener('resize',onResize)
    window.addEventListener('hashchange',onHash)
    return()=>{
      observer.disconnect()
      window.removeEventListener('resize',onResize)
      window.removeEventListener('hashchange',onHash)
    }
  },[])
  return null
}
