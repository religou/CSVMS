import { useEffect, useState } from 'react'
import dictService, { type DictItem } from '@/services/dictionary'

export interface UseDictItemsOptions {
    /** 是否只返回已启用的字典项，默认 true（与既有调用行为一致） */
    enabledOnly?: boolean
}

/**
 * 获取指定字典类别的选项列表。
 * 每次组件挂载时重新请求，不做缓存。
 */
export function useDictItems(
    categoryCode: string,
    options?: UseDictItemsOptions,
) {
    const enabledOnly = options?.enabledOnly ?? true
    const [items, setItems] = useState<DictItem[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<unknown>(null)

    useEffect(() => {
        let cancelled = false
        setLoading(true)
        setError(null)
        dictService
            .listItems(categoryCode, enabledOnly)
            .then((data) => {
                if (!cancelled) setItems(data)
            })
            .catch((err) => {
                if (!cancelled) {
                    setItems([])
                    setError(err)
                }
            })
            .finally(() => {
                if (!cancelled) setLoading(false)
            })
        return () => {
            cancelled = true
        }
    }, [categoryCode, enabledOnly])

    const selectOptions = items.map((item) => ({
        value: item.code,
        label: item.label,
    }))

    return { items, options: selectOptions, loading, error }
}
