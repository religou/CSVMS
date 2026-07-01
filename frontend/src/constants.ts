/**
 * 共享常量 - 文档类型、状态映射等。
 * 避免在各页面重复定义。
 */

export const DOC_TYPES = [
    'VP',
    'URS',
    'FS',
    'DS',
    'IQ',
    'OQ',
    'PQ',
    'TM',
    'VSR',
    'DV',
    'CC',
    'PR',
    'RET',
] as const

export const DOC_TYPE_LABELS: Record<string, string> = {
    VP: 'VP（Validation Plan）',
    URS: 'URS（User Requirement Specification）',
    FS: 'FS（Functional Specification）',
    DS: 'DS（Design Specification）',
    IQ: 'IQ（Installation Qualification）',
    OQ: 'OQ（Operational Qualification）',
    PQ: 'PQ（Performance Qualification）',
    TM: 'TM（Traceability Matrix）',
    VSR: 'VSR（Validation Summary Report）',
    DV: 'DV（Deviation）',
    CC: 'CC（Change Control）',
    PR: 'PR（Periodic Review）',
    RET: 'RET（Retirement）',
}

export const STATUS_OPTIONS = [
    { value: 'draft', label: '草稿', color: 'default' },
    { value: 'under_review', label: '审核中', color: 'processing' },
    { value: 'approved', label: '已批准', color: 'success' },
    { value: 'effective', label: '已生效', color: 'green' },
    { value: 'superseded', label: '已替代', color: 'warning' },
    { value: 'retired', label: '已废止', color: 'error' },
] as const

export const STATUS_MAP: Record<string, { label: string; color: string }> =
    Object.fromEntries(
        STATUS_OPTIONS.map((s) => [
            s.value,
            { label: s.label, color: s.color },
        ]),
    )

export const WF_STATUS_LABELS: Record<string, string> = {
    pending: '待处理',
    in_progress: '进行中',
    approved: '已完成',
    rejected: '已拒绝',
    cancelled: '已撤回',
}
