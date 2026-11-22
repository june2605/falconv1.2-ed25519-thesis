import { test, expect, type Page } from '@playwright/test'
import { mkdir } from 'node:fs/promises'
import { go } from './helpers'
import { responsiveHost, publicId } from './support/native-responsive-host'

const sizes = [[960,600],[1100,700],[1177,740],[1280,800],[1366,768],[1440,900],[1920,1080]]
const sidebar = (page: Page) => page.getByRole('complementary', { name: 'Workspace sidebar', exact: true })
async function compact(page: Page) {
  await page.setViewportSize({ width: 1100, height: 700 })
  await go(page, 'verify')
  await expect(sidebar(page)).toHaveAttribute('data-expanded', 'false')
}
async function metrics(page: Page) {
  return page.evaluate(() => {
    const main=document.querySelector('main')!, footer=document.querySelector('.task-actions-host')!, box=main.getBoundingClientRect()
    return { left:box.left, width:box.width, scroll:main.scrollTop, columns:getComputedStyle(document.querySelector('.workflow-grid')!).gridTemplateColumns,
      footer:footer.getBoundingClientRect().left, overflow:document.documentElement.scrollWidth>innerWidth||main.scrollWidth>main.clientWidth }
  })
}

test('Auto stays compact outside at every size and pin availability uses width hysteresis', async ({ page }) => {
  await responsiveHost(page)
  await compact(page)
  for(const [width,height] of sizes) {
    await page.setViewportSize({width,height})
    await page.mouse.move(width-10,100)
    await expect(sidebar(page)).toHaveAttribute('data-docked', 'false')
    await expect(sidebar(page)).toHaveAttribute('data-expanded', 'false')
    expect((await metrics(page)).overflow).toBe(false)
    await expect(page.getByRole('heading',{name:'HYBRID VALID',exact:true})).toBeVisible()
    {
      await page.getByRole('button',{name:'Expand sidebar',exact:true}).click()
      await expect.poll(()=>page.locator('main').evaluate(node=>node.getBoundingClientRect().left)).toBe(250)
      expect((await metrics(page)).overflow).toBe(false)
      await expect(page.getByRole('button',{name:'Verify PDF',exact:true})).toBeInViewport()
      const noCover=await page.evaluate(()=>document.querySelector('main')!.getBoundingClientRect().left>=document.querySelector('.smart-sidebar')!.getBoundingClientRect().right)
      expect(noCover).toBe(true)
      if(width>=1340) await expect(page.getByRole('button',{name:'Pin sidebar',exact:true})).toBeEnabled()
      await page.keyboard.press('Escape')
      await expect.poll(()=>page.locator('main').evaluate(node=>node.getBoundingClientRect().left)).toBe(72)
    }
  }
  for(const width of [1320,1300,1281]) {
    await page.setViewportSize({width,height:768})
    await page.getByRole('button',{name:'Expand sidebar',exact:true}).click()
    await expect(page.getByRole('button',{name:'Pin sidebar',exact:true})).toBeEnabled()
    await page.keyboard.press('Escape')
  }
  await page.setViewportSize({width:1280,height:768})
  await expect(sidebar(page)).toHaveAttribute('data-docked','false')
  for(const width of [1281,1300,1339]) {
    await page.setViewportSize({width,height:768})
    await expect(sidebar(page)).toHaveAttribute('data-docked','false')
    await page.getByRole('button',{name:'Expand sidebar',exact:true}).click()
    await expect(page.getByRole('button',{name:'Pin sidebar',exact:true})).toBeDisabled()
    await page.keyboard.press('Escape')
  }
})

test('delayed hover reserves page space without covering content and collapses after leave', async ({ page }) => {
  await responsiveHost(page); await compact(page)
  await page.locator('main').evaluate(node=>{node.scrollTop=80})
  const before=await metrics(page)
  const routeBefore=await page.getByRole('link',{name:'Verify Signature',exact:true}).boundingBox()
  await page.mouse.move(30,170)
  await expect(sidebar(page)).toHaveAttribute('data-expanded','true')
  const opening = await page.evaluate(async () => {
    const samples: boolean[]=[]
    const until=performance.now()+250
    while(performance.now()<until) {
      await new Promise(requestAnimationFrame)
      const side=document.querySelector('.smart-sidebar')!.getBoundingClientRect()
      const main=document.querySelector('main')!.getBoundingClientRect()
      const header=document.querySelector('.topbar')!.getBoundingClientRect()
      const footer=document.querySelector('.task-actions-host')!.getBoundingClientRect()
      samples.push(main.left>=side.right-.5 && header.left>=side.right-.5 && footer.left>=side.right-.5)
    }
    return samples
  })
  expect(opening.length).toBeGreaterThan(1)
  expect(opening.every(Boolean)).toBe(true)
  const routeAfter=await page.getByRole('link',{name:'Verify Signature',exact:true}).boundingBox()
  expect(routeAfter!.y).toBe(routeBefore!.y)
  expect(routeAfter!.height).toBe(routeBefore!.height)
  await expect(sidebar(page)).toHaveAttribute('data-docked','false')
  await page.mouse.move(205,210)
  await expect(sidebar(page)).toHaveAttribute('data-expanded','true')
  const expanded=await metrics(page)
  expect(expanded.left).toBe(250)
  expect(expanded.footer).toBe(250)
  expect(expanded.width).toBe(before.width-178)
  expect(expanded.scroll).toBe(before.scroll)
  expect(expanded.overflow).toBe(false)
  await page.mouse.move(800,200)
  await expect(sidebar(page)).toHaveAttribute('data-expanded','false')
  const closing = await page.evaluate(async () => {
    const samples: boolean[]=[]
    const until=performance.now()+250
    while(performance.now()<until) {
      await new Promise(requestAnimationFrame)
      samples.push(document.querySelector('main')!.getBoundingClientRect().left>=document.querySelector('.smart-sidebar')!.getBoundingClientRect().right-.5)
    }
    return samples
  })
  expect(closing.length).toBeGreaterThan(1)
  expect(closing.every(Boolean)).toBe(true)
  expect(await metrics(page)).toEqual(before)
})

test('manual control, pin, unpin and narrow-window safety keep a single navigation tree', async ({ page }) => {
  await responsiveHost(page)
  await page.setViewportSize({width:1440,height:900}); await go(page,'verify')
  await page.getByRole('button',{name:'Expand sidebar',exact:true}).click()
  await page.getByRole('button',{name:'Collapse sidebar',exact:true}).click()
  await expect(sidebar(page)).toHaveAttribute('data-docked','false')
  await page.getByRole('button',{name:'Expand sidebar',exact:true}).click()
  await expect(sidebar(page)).toHaveAttribute('data-expanded','true')
  await page.getByRole('button',{name:'Pin sidebar',exact:true}).click()
  await expect(sidebar(page)).toHaveAttribute('data-mode','pinned')
  await expect(sidebar(page)).toHaveAttribute('data-docked','true')
  await page.setViewportSize({width:960,height:600})
  await expect(sidebar(page)).toHaveAttribute('data-docked','false')
  await page.getByRole('button',{name:'Expand sidebar',exact:true}).click()
  await expect(page.getByRole('button',{name:'Unpin sidebar',exact:true})).toBeEnabled()
  await page.keyboard.press('Escape')
  await page.setViewportSize({width:1440,height:900})
  await expect(sidebar(page)).toHaveAttribute('data-docked','true')
  await page.getByRole('button',{name:'Unpin sidebar',exact:true}).click()
  await expect(sidebar(page)).toHaveAttribute('data-docked','false')
  await page.keyboard.press('Escape')
  await expect(sidebar(page)).toHaveAttribute('data-expanded','false')
  await expect(page.getByRole('navigation',{name:'Main navigation'})).toHaveCount(1)
  await expect(sidebar(page).locator('nav a')).toHaveCount(5)
})

test('keyboard focus holds the temporary panel and Escape returns hidden-control focus safely', async ({ page }) => {
  await responsiveHost(page); await compact(page)
  const expand=page.getByRole('button',{name:'Expand sidebar',exact:true})
  await expand.focus(); await page.keyboard.press('Enter')
  await expect(sidebar(page)).toHaveAttribute('data-expanded','true')
  await page.getByRole('button',{name:'Automatic sidebar',exact:true}).focus()
  await page.keyboard.press('Escape')
  await expect(sidebar(page)).toHaveAttribute('data-expanded','false')
  await expect(expand).toBeFocused()
  await page.keyboard.press('Enter')
  await page.getByRole('link',{name:'Key Vault',exact:true}).focus()
  await page.mouse.move(900,400)
  await expect(sidebar(page)).toHaveAttribute('data-expanded','true')
  await page.keyboard.press('Escape')
  await expect(sidebar(page)).toHaveAttribute('data-expanded','false')
  await expect(page.getByRole('link',{name:'Key Vault',exact:true})).toBeFocused()
  await page.getByRole('link',{name:'Settings',exact:true}).focus(); await page.keyboard.press('Enter')
  await expect(page.getByRole('link',{name:'Settings',exact:true})).toHaveAttribute('aria-current','page')
  await expect(page.locator('h1')).toBeFocused()
})

test('rapid pointer transitions and resizing do not leave a stale hover panel', async ({ page }) => {
  await page.clock.install()
  await responsiveHost(page); await compact(page)
  await page.clock.pauseAt(new Date(Date.now()+60000))
  for(let index=0;index<4;index++) {
    await page.mouse.move(30,180); await page.clock.runFor(60)
    await page.mouse.move(900,180); await page.clock.runFor(60)
  }
  await page.clock.runFor(400)
  await expect(sidebar(page)).toHaveAttribute('data-expanded','false')
  await page.mouse.move(30,180)
  await page.setViewportSize({width:1177,height:740})
  // Setting the viewport can return before Chromium dispatches window.resize.
  // Keep the clock paused until React has handled that event and cleared the
  // pending hover timer. Advancing sooner races the event we intend to test.
  await expect(sidebar(page)).toHaveAttribute('data-resizing','true')
  await page.clock.runFor(500)
  await expect(sidebar(page)).toHaveAttribute('data-resizing','false')
  await expect(sidebar(page)).toHaveAttribute('data-expanded','false')
  expect((await metrics(page)).overflow).toBe(false)
})

test('coarse pointer and reduced motion preserve explicit controls and accessible tooltips', async ({ page, browser }) => {
  await responsiveHost(page)
  await page.emulateMedia({reducedMotion:'reduce'})
  await compact(page)
  await expect(sidebar(page)).toHaveCSS('transition-duration','0s')
  await expect(page.getByRole('link',{name:'Dashboard',exact:true})).toHaveAttribute('aria-label','Dashboard')
  await page.getByRole('button',{name:'Expand sidebar',exact:true}).focus()
  await expect(page.getByRole('tooltip')).toContainText('Expand sidebar')
  await page.keyboard.press('Enter')
  await expect(sidebar(page)).toHaveAttribute('data-expanded','true')
  await page.keyboard.press('Escape')
  await expect(sidebar(page)).toHaveAttribute('data-expanded','false')
  const context=await browser.newContext({baseURL:'http://127.0.0.1:4173',viewport:{width:1100,height:700},hasTouch:true})
  try {
    const touch=await context.newPage(); await responsiveHost(touch); await compact(touch)
    expect(await touch.evaluate(()=>matchMedia('(pointer: coarse)').matches)).toBe(true)
    await touch.clock.install(); await touch.clock.pauseAt(new Date(Date.now()+60000))
    await touch.mouse.move(30,180); await touch.clock.runFor(500)
    await expect(sidebar(touch)).toHaveAttribute('data-expanded','false')
    await touch.getByRole('button',{name:'Expand sidebar',exact:true}).tap()
    await expect(sidebar(touch)).toHaveAttribute('data-expanded','true')
    await touch.getByRole('button',{name:'Collapse sidebar',exact:true}).tap()
    await expect(sidebar(touch)).toHaveAttribute('data-expanded','false')
  } finally { await context.close() }
})

test('all routes and native vault, selected signing document and verification state survive sidebar changes', async ({ page }) => {
  await responsiveHost(page); await compact(page)
  await page.getByRole('button',{name:'Expand sidebar',exact:true}).click()
  await page.getByRole('link',{name:'Sign Document',exact:true}).click()
  await page.getByRole('button',{name:'Choose PDF',exact:true}).click()
  await page.getByRole('button',{name:'Continue to review',exact:true}).click()
  for(let index=0;index<2;index++) {
    await page.getByRole('button',{name:'Expand sidebar',exact:true}).click()
    await page.keyboard.press('Escape')
  }
  await expect(page.getByRole('button',{name:'Review and sign step',exact:true})).toHaveAttribute('aria-expanded','true')
  await expect(page.getByRole('button',{name:'Sign PDF',exact:true})).toBeEnabled()
  for(const [name,title] of [['Dashboard','Dashboard'],['Key Vault','Manage your signing keys'],['Settings','Settings'],['Verify Signature','Verify a signature']]) {
    await page.getByRole('link',{name,exact:true}).click()
    await expect(page.locator('h1')).toHaveText(title)
    await expect(page.getByRole('link',{name,exact:true})).toHaveAttribute('aria-current','page')
  }
  await expect(page.getByRole('heading',{name:'HYBRID VALID',exact:true})).toBeVisible()
  await expect(page.locator('main')).toContainText(publicId)
  await page.getByRole('link',{name:'Key Vault',exact:true}).click()
  await expect(page.locator('.vault-status-line')).toContainText('Unlocked')
  await page.getByRole('link',{name:'Sign Document',exact:true}).click()
  await expect(page.locator('main')).toContainText('Research document with a longer filename.pdf')
  expect(await page.evaluate(()=>({local:localStorage.length,session:sessionStorage.length}))).toEqual({local:0,session:0})
})

test('sidebar modes remain readable in both themes and representative captures', async ({ page }, info) => {
  await responsiveHost(page); await compact(page)
  for(const theme of ['light','dark']) {
    await page.getByRole('link',{name:'Settings',exact:true}).click()
    await page.getByRole('radio',{name:new RegExp(theme,'i')}).check()
    await page.getByRole('link',{name:'Verify Signature',exact:true}).click()
    for(const [width,height] of [[960,600],[1177,740],[1366,768]]) {
      await page.setViewportSize({width,height})
      await page.mouse.move(width-10,100)
      await expect(sidebar(page)).toHaveAttribute('data-docked','false')
      await expect(page.locator('.preview-indicator')).toHaveText('Desktop')
      if(info.project.name==='desktop-1366') {
        await mkdir('qa/phase4b3b1-interactions',{recursive:true})
        await page.screenshot({path:`qa/phase4b3b1-interactions/${width}x${height}-${theme}.png`,animations:'disabled'})
        {
          await page.getByRole('button',{name:'Expand sidebar',exact:true}).click()
          await expect.poll(()=>page.locator('main').evaluate(node=>node.getBoundingClientRect().left)).toBe(250)
          await page.screenshot({path:`qa/phase4b3b1-interactions/${width}x${height}-${theme}-expanded.png`,animations:'disabled'})
          await page.keyboard.press('Escape')
        }
      }
    }
  }
})

test('sidebar changes cannot cancel or reset an active native signing job', async ({ page }) => {
  await responsiveHost(page,'valid','unauthenticated-metadata','running')
  await page.setViewportSize({width:1100,height:700}); await go(page,'sign')
  await expect(page.getByText('Signing and checking the PDF…',{exact:true})).toBeVisible()
  await page.getByRole('button',{name:'Expand sidebar',exact:true}).click()
  await page.keyboard.press('Escape')
  await page.setViewportSize({width:1440,height:900})
  await page.getByRole('button',{name:'Expand sidebar',exact:true}).click()
  await page.getByRole('button',{name:'Collapse sidebar',exact:true}).click()
  await expect(page.getByText('Signing and checking the PDF…',{exact:true})).toBeVisible()
  await expect(page.getByRole('button',{name:'Sign PDF',exact:true})).toBeDisabled()
  await page.getByRole('link',{name:'Key Vault',exact:true}).click()
  await expect(page.locator('.vault-status-line')).toContainText('Unlocked')
  await expect(page.getByRole('button',{name:'Lock Vault',exact:true})).toBeDisabled()
  await page.getByRole('link',{name:'Verify Signature',exact:true}).click()
  await expect(page.getByRole('heading',{name:'HYBRID VALID',exact:true})).toBeVisible()
})
