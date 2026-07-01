import { useEffect, useState } from 'react'
import dictService, { type DictItem } from '@/services/dictionary'

/**
 * 获取指定字典类别的选项列表。
 * 每次组件挂载时重新请求，不做缓存。
 */
export function useDictItems(categoryCode: string) {
    const [items, setItems] = useState<DictItem[]>([])
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        let cancelled = false
        setLoading(true)
        dictService
            .listItems(categoryCode)
            .then((data) => {
                if (!cancelled) setItems(data)
            })
            .catch(() => {
                /* ignore */
            })
            .finally(() => {
                if (!cancelled) setLoading(false)
            })
        return () => {
            cancelled = true
        }
    }, [categoryCode])

    const options = items.map((item) => ({
        value: item.code,
        label: item.label,
    }))

    return { items, options, loading }
}
