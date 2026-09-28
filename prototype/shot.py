import asyncio, sys
from playwright.async_api import async_playwright
URL='file://'+sys.argv[1]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        for name,(w,h),scheme in [('desk',(1440,900),'light'),('mob',(390,844),'light'),('dark',(1440,900),'dark'),('tab',(1024,768),'light')]:
            pg=await b.new_page(viewport={'width':w,'height':h},color_scheme=scheme)
            pg.on('console',lambda m: errs.append(f'{name} {m.type}: {m.text}') if m.type in('error','warning') else None)
            pg.on('pageerror',lambda e: errs.append(f'{name} PAGEERROR {e}'))
            await pg.goto(URL); await pg.wait_for_timeout(7200)
            await pg.screenshot(path=f's_{name}_0cold.png')
            H=await pg.evaluate('document.getElementById("hq").offsetHeight - innerHeight')
            for frac,lab in [(.2,'1a'),(.3,'1mid'),(.55,'2mid'),(1.0,'3final')]:
                await pg.evaluate(f'window.scrollTo(0,{int(H*frac)})'); await pg.wait_for_timeout(500)
                await pg.screenshot(path=f's_{name}_{lab}.png')
            if name!='dark' or True:
                y=await pg.evaluate('document.getElementById("b06").getBoundingClientRect().top + scrollY - 40')
                await pg.evaluate(f'window.scrollTo(0,{int(y)})'); await pg.wait_for_timeout(500)
                await pg.screenshot(path=f's_{name}_4block.png')
                y=await pg.evaluate('document.getElementById("fig1").getBoundingClientRect().top + scrollY - 60')
                await pg.evaluate(f'window.scrollTo(0,{int(y)})'); await pg.wait_for_timeout(500)
                await pg.screenshot(path=f's_{name}_5fig1.png')
                y=await pg.evaluate('document.getElementById("fig2").getBoundingClientRect().top + scrollY - 80')
                await pg.evaluate(f'window.scrollTo(0,{int(y)})'); await pg.wait_for_timeout(2000)
                await pg.screenshot(path=f's_{name}_6fig2.png')
            ov=await pg.evaluate('document.documentElement.scrollWidth > innerWidth'); print(name,'hscroll',ov)
            await pg.close()
        print('\n'.join(errs) or 'no console errors'); await b.close()
asyncio.run(main())
