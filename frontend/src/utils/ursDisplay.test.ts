import fc from 'fast-check'
import { describe, expect, it } from 'vitest'
import type { UrsItem, UrsReference } from '../services/documents'
import { formatUrsItemRows, formatUrsReferenceRows, isUncoveredHighlighted } from './ursDisplay'

function buildUrsItem(partial: {
    id: string
    document_id: string
    item_code: string
    description: string
}): UrsItem {
    return {
        id: partial.id,
        document_id: partial.document_id,
        item_code: partial.item_code,
        description: partial.description,
        created_at: '2024-01-01T00:00:00Z',
    }
}

function buildUrsReference(partial: {
    id: string
    document_id: string
    urs_item_id: string
    item_code: string
    description: string
    source_document_id: string
    source_doc_number: string
}): UrsReference {
    return {
        id: partial.id,
        document_id: partial.document_id,
        urs_item_id: partial.urs_item_id,
        item_code: partial.item_code,
        description: partial.description,
        source_document_id: partial.source_document_id,
        source_doc_number: partial.source_doc_number,
        created_at: '2024-01-01T00:00:00Z',
    }
}

const ursItemArbitrary: fc.Arbitrary<UrsItem> = fc
    .record({
        id: fc.uuid(),
        document_id: fc.uuid(),
        item_code: fc.string({ maxLength: 20 }),
        description: fc.string({ maxLength: 100 }),
    })
    .map(buildUrsItem)

const ursItemsArbitrary = fc.array(ursItemArbitrary, { maxLength: 10 })

const ursReferenceArbitrary: fc.Arbitrary<UrsReference> = fc
    .record({
        id: fc.uuid(),
        document_id: fc.uuid(),
        urs_item_id: fc.uuid(),
        item_code: fc.string({ maxLength: 20 }),
        description: fc.string({ maxLength: 100 }),
        source_document_id: fc.uuid(),
        source_doc_number: fc.string({ maxLength: 20 }),
    })
    .map(buildUrsReference)

const ursReferencesArbitrary = fc.array(ursReferenceArbitrary, { maxLength: 10 })

describe('formatUrsItemRows property tests', () => {
    it(
        // Feature: urs-traceability-matrix, Property 10: 文档详情列表渲染的字段完整性
        // Validates: Requirements 4.1, 4.3
        'produces exactly one output row per input URS_Item, preserving item_code and description',
        () => {
            fc.assert(
                fc.property(ursItemsArbitrary, (items) => {
                    const rows = formatUrsItemRows(items)

                    expect(rows).toHaveLength(items.length)

                    rows.forEach((row, index) => {
                        expect(row.itemCode).toBe(items[index].item_code)
                        expect(row.description).toBe(items[index].description)
                    })
                }),
                { numRuns: 100 },
            )
        },
    )
})

describe('formatUrsReferenceRows property tests', () => {
    it(
        // Feature: urs-traceability-matrix, Property 10: 文档详情列表渲染的字段完整性
        // Validates: Requirements 4.1, 4.3
        'produces exactly one output row per input URS_Reference, preserving item_code, description and source_doc_number',
        () => {
            fc.assert(
                fc.property(ursReferencesArbitrary, (refs) => {
                    const rows = formatUrsReferenceRows(refs)

                    expect(rows).toHaveLength(refs.length)

                    rows.forEach((row, index) => {
                        expect(row.itemCode).toBe(refs[index].item_code)
                        expect(row.description).toBe(refs[index].description)
                        expect(row.sourceDocNumber).toBe(refs[index].source_doc_number)
                    })
                }),
                { numRuns: 100 },
            )
        },
    )
})
describe('isUncoveredHighlighted property tests', () => {
    it(
        // Feature: urs-traceability-matrix, Property 12: 未覆盖条目的高亮渲染判定
        // Validates: Requirements 5.3
        'returns true if and only if itemId is present in uncoveredIds',
        () => {
            fc.assert(
                fc.property(
                    fc.string(),
                    fc.array(fc.string()),
                    (itemId, uncoveredIds) => {
                        const result = isUncoveredHighlighted(itemId, uncoveredIds)
                        expect(result).toBe(uncoveredIds.includes(itemId))
                    },
                ),
                { numRuns: 100 },
            )
        },
    )
})
