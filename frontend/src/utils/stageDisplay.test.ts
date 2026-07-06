import fc from 'fast-check'
import { describe, expect, it } from 'vitest'
import type { DictItem } from '../services/dictionary'
import {
    deriveEnabledStageOptions,
    isRenderableColor,
    resolveStageDisplay,
} from './stageDisplay'

const UNSET_LABEL = '未设置'
const UNKNOWN_LABEL = '未知阶段'

function buildDictItem(partial: {
    code: string
    label: string
    extra: string | null
    is_enabled: boolean
    sort_order?: number
}): DictItem {
    return {
        id: 'id',
        category_id: 'category-id',
        code: partial.code,
        label: partial.label,
        description: null,
        sort_order: partial.sort_order ?? 0,
        is_enabled: partial.is_enabled,
        extra: partial.extra,
        permission_profile: null,
        permission_codes: null,
        created_at: '2024-01-01T00:00:00Z',
    }
}

const dictItemArbitrary: fc.Arbitrary<DictItem> = fc
    .record({
        code: fc.string({ maxLength: 10 }),
        label: fc.string({ maxLength: 20 }),
        extra: fc.oneof(
            fc.constant(null),
            fc.string({ maxLength: 15 }),
            fc.constantFrom(
                'red',
                'blue',
                'PURPLE',
                '#fff',
                '#123456',
                '#12345678',
            ),
        ),
        is_enabled: fc.boolean(),
    })
    .map(buildDictItem)

const itemsArbitrary = fc.array(dictItemArbitrary, { maxLength: 6 })

type CodeSelector =
    | { kind: 'null' }
    | { kind: 'undefined' }
    | { kind: 'emptyString' }
    | { kind: 'random'; value: string }
    | { kind: 'indexed'; index: number }

const codeSelectorArbitrary: fc.Arbitrary<CodeSelector> = fc.oneof(
    fc.constant<CodeSelector>({ kind: 'null' }),
    fc.constant<CodeSelector>({ kind: 'undefined' }),
    fc.constant<CodeSelector>({ kind: 'emptyString' }),
    fc.record({
        kind: fc.constant('random' as const),
        value: fc.string({ maxLength: 10 }),
    }),
    fc.record({
        kind: fc.constant('indexed' as const),
        index: fc.nat(),
    }),
)

function resolveStageCode(
    selector: CodeSelector,
    items: DictItem[],
): string | null | undefined {
    switch (selector.kind) {
        case 'null':
            return null
        case 'undefined':
            return undefined
        case 'emptyString':
            return ''
        case 'random':
            return selector.value
        case 'indexed':
            return items[selector.index % items.length].code
    }
}

describe('resolveStageDisplay property tests', () => {
    it(
        // Feature: project-stage-management, Property 8: 阶段展示的标签与颜色解析
        // Validates: Requirements 4.1, 4.3, 4.4, 4.5, 4.6, 6.1, 6.2, 6.3
        'resolves stage code + dict items to the expected label/color/matched combination',
        () => {
            fc.assert(
                fc.property(
                    itemsArbitrary,
                    codeSelectorArbitrary,
                    (items, selector) => {
                        fc.pre(selector.kind !== 'indexed' || items.length > 0)
                        const stageCode = resolveStageCode(selector, items)

                        const actual = resolveStageDisplay(stageCode, items)

                        if (!stageCode) {
                            expect(actual).toEqual({
                                label: UNSET_LABEL,
                                matched: false,
                            })
                            return
                        }

                        const matchedItem = items.find(
                            (item) => item.code === stageCode,
                        )

                        if (!matchedItem) {
                            expect(actual).toEqual({
                                label: UNKNOWN_LABEL,
                                matched: false,
                            })
                            return
                        }

                        expect(actual.matched).toBe(true)
                        expect(actual.label).toBe(matchedItem.label)

                        if (isRenderableColor(matchedItem.extra)) {
                            expect(actual.color).toBe(matchedItem.extra)
                        } else {
                            expect(actual.color).toBeUndefined()
                        }
                    },
                ),
                { numRuns: 100 },
            )
        },
    )
})

const stageOptionDictItemArbitrary: fc.Arbitrary<DictItem> = fc
    .record({
        code: fc.string({ maxLength: 10 }),
        label: fc.string({ maxLength: 20 }),
        extra: fc.constant(null),
        is_enabled: fc.boolean(),
        sort_order: fc.integer({ min: -100, max: 100 }),
    })
    .map(buildDictItem)

// Codes are unique within a dictionary category (Property 1), so constrain the
// generated items accordingly to avoid ambiguous label lookups in the assertions.
const stageOptionItemsArbitrary = fc.uniqueArray(stageOptionDictItemArbitrary, {
    maxLength: 10,
    selector: (item) => item.code,
})

describe('deriveEnabledStageOptions property tests', () => {
    it(
        // Feature: project-stage-management, Property 9: 可选阶段列表的过滤与排序
        // Validates: Requirements 5.1
        'derives exactly the enabled items sorted ascending by sort_order, or an empty list when none are enabled',
        () => {
            fc.assert(
                fc.property(stageOptionItemsArbitrary, (items) => {
                    const actual = deriveEnabledStageOptions(items)

                    const enabledItems = items.filter((item) => item.is_enabled)

                    if (enabledItems.length === 0) {
                        expect(actual).toEqual([])
                        return
                    }

                    // Same set of items (by code), independent of ordering.
                    expect(actual.map((option) => option.value).sort()).toEqual(
                        enabledItems.map((item) => item.code).sort(),
                    )

                    // Every returned option's label matches its source item's label.
                    const labelByCode = new Map(
                        enabledItems.map((item) => [item.code, item.label]),
                    )
                    for (const option of actual) {
                        expect(option.label).toBe(labelByCode.get(option.value))
                    }

                    // Ascending sort_order.
                    const expectedOrder = [...enabledItems]
                        .sort((a, b) => a.sort_order - b.sort_order)
                        .map((item) => item.code)
                    expect(actual.map((option) => option.value)).toEqual(
                        expectedOrder,
                    )
                }),
                { numRuns: 100 },
            )
        },
    )
})
