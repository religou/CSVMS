import type { UrsItem, UrsReference } from '../services/documents'

// ---------- Types ----------

export interface UrsReferenceRow {
    itemCode: string
    description: string
    sourceDocNumber: string
}

export interface UrsItemRow {
    itemCode: string
    description: string
}

/**
 * 将 URS_Reference 记录列表映射为文档详情页表格渲染所需的最小字段集合。
 * 每条输入记录生成恰好一行输出，完整保留条目编号、描述与来源 URS 文档编号。
 */
export function formatUrsReferenceRows(refs: UrsReference[]): UrsReferenceRow[] {
    return refs.map((ref) => ({
        itemCode: ref.item_code,
        description: ref.description,
        sourceDocNumber: ref.source_doc_number,
    }))
}

/**
 * 将 URS_Item 记录列表映射为文档详情页表格渲染所需的最小字段集合。
 * 每条输入记录生成恰好一行输出，完整保留条目编号与描述字段值。
 */
export function formatUrsItemRows(items: UrsItem[]): UrsItemRow[] {
    return items.map((item) => ({
        itemCode: item.item_code,
        description: item.description,
    }))
}

/**
 * 判断给定条目 id 是否应在追溯矩阵页面以红色高亮渲染：
 * 当且仅当该条目 id 存在于后端返回的未覆盖条目 id 列表中。
 */
export function isUncoveredHighlighted(itemId: string, uncoveredIds: string[]): boolean {
    return uncoveredIds.includes(itemId)
}
