const preloadedImages = new Map<string, HTMLImageElement>()

export function preloadImage(src: string): Promise<HTMLImageElement> {
  if (preloadedImages.has(src)) {
    return Promise.resolve(preloadedImages.get(src)!)
  }
  
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      preloadedImages.set(src, img)
      resolve(img)
    }
    img.onerror = reject
    img.src = src
  })
}

export function preloadHorseGif(): Promise<HTMLImageElement> {
  const gifUrl = new URL('@/assets/horse-running.gif', import.meta.url).href
  return preloadImage(gifUrl)
}
