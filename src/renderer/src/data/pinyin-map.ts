// 拼音分组映射表 - 通用模糊匹配
// 同拼音的汉字归为一组，用于唤醒词容错识别

// 拼音分组数据，从 pinyin-data.ts 导入
import { pinyinGroups } from './pinyin-data'

// 反向索引：汉字 -> 拼音组key
const charToPinyin: Map<string, string> = new Map()

// 初始化反向索引
function initIndex() {
  const keys = Object.keys(pinyinGroups)
  for (let k = 0; k < keys.length; k++) {
    const pinyin = keys[k]
    const chars: string = (pinyinGroups as Record<string, string>)[pinyin]
    for (let i = 0; i < chars.length; i++) {
      charToPinyin.set(chars[i], pinyin)
    }
  }
}
initIndex()

/**
 * 检查两个汉字是否同音（在同一拼音分组中）
 */
export function isSamePinyin(a: string, b: string): boolean {
  const pA = charToPinyin.get(a)
  const pB = charToPinyin.get(b)
  if (!pA || !pB) return a === b
  return pA === pB
}

/**
 * 模糊匹配唤醒词
 * text: 识别到的文本（可能包含前后缀如"你好小马"、"小马啊"）
 * wakeWord: 唤醒词（如"小马"）
 */
export function matchesWakeWord(text: string, wakeWord: string): boolean {
  if (!text || !wakeWord) return false
  if (text.indexOf(wakeWord) !== -1) return true

  const textChars = Array.from(text)
  const wakeChars = Array.from(wakeWord)
  const wakeLen = wakeChars.length

  for (let i = 0; i <= textChars.length - wakeLen; i++) {
    let matched = true
    for (let j = 0; j < wakeLen; j++) {
      if (!isSamePinyin(textChars[i + j], wakeChars[j])) {
        matched = false
        break
      }
    }
    if (matched) return true
  }
  return false
}

/**
 * 返回匹配到的子串（用于调试/可视化）
 */
export function findMatchSubstring(text: string, wakeWord: string): string | null {
  if (!text || !wakeWord) return null
  if (text.indexOf(wakeWord) !== -1) return wakeWord

  const textChars = Array.from(text)
  const wakeChars = Array.from(wakeWord)
  const wakeLen = wakeChars.length

  for (let i = 0; i <= textChars.length - wakeLen; i++) {
    let matched = true
    for (let j = 0; j < wakeLen; j++) {
      if (!isSamePinyin(textChars[i + j], wakeChars[j])) {
        matched = false
        break
      }
    }
    if (matched) return textChars.slice(i, i + wakeLen).join('')
  }
  return null
}
