import type { DictItem } from '../services/dictionary'

export interface StageDisplayResult {
    label: string
    color?: string
    matched: boolean // 是否命中某个字典项（不区分启用/禁用）
}

const UNSET_LABEL = '未设置'
const UNKNOWN_LABEL = '未知阶段'

// Ant Design 预设颜色名称（Tag/Badge 等组件支持的语义化颜色）
const ANTD_PRESET_COLORS = new Set([
    'pink',
    'red',
    'yellow',
    'orange',
    'cyan',
    'green',
    'blue',
    'purple',
    'geekblue',
    'magenta',
    'volcano',
    'gold',
    'lime',
    'default',
    'success',
    'processing',
    'error',
    'warning',
])

const HEX_COLOR_REGEX = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/

/**
 * 判断给定的 `extra` 字符串是否是一个可用于渲染的颜色值。
 * 支持 Ant Design 预设颜色名称与十六进制颜色（#fff / #ffffff / #ffffffff）。
 * 空值、空字符串（含空白字符）或无法识别的取值均视为不可渲染。
 */
export function isRenderableColor(extra: string | null | undefined): boolean {
    if (!extra) {
        return false
    }
    const trimmed = extra.trim()
    if (trimmed.length === 0) {
        return false
    }
    if (HEX_COLOR_REGEX.test(trimmed)) {
        return true
    }
    return ANTD_PRESET_COLORS.has(trimmed.toLowerCase())
}

/**
 * 将阶段编码解析为可展示的标签文本与（可选）颜色。
 * - 阶段编码为空（null/undefined/空字符串）→ 未设置占位
 * - 阶段编码有值但在字典项集合中找不到匹配的 code → 未知阶段占位
 * - 阶段编码有值且找到匹配的字典项（不论 is_enabled）→ 返回其 label，
 *   仅当该字典项的 extra 是可解析颜色时附带 color
 */
export function resolveStageDisplay(
    stageCode: string | null | undefined,
    items: DictItem[],
): StageDisplayResult {
    if (!stageCode) {
        return { label: UNSET_LABEL, matched: false }
    }

    const matchedItem = items.find((item) => item.code === stageCode)
    if (!matchedItem) {
        return { label: UNKNOWN_LABEL, matched: false }
    }

    const result: StageDisplayResult = { label: matchedItem.label, matched: true }
    if (isRenderableColor(matchedItem.extra)) {
        result.color = matchedItem.extra as string
    }
    return result
}

/**
 * 从字典项集合中推导可选阶段列表：仅保留已启用项，并按 sort_order 升序排列。
 */
export function deriveEnabledStageOptions(
    items: DictItem[],
): { value: string; label: string }[] {
    return items
        .filter((item) => item.is_enabled)
        .sort((a, b) => a.sort_order - b.sort_order)
        .map((item) => ({ value: item.code, label: item.label }))
}
