import { useEffect, useRef } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import Underline from '@tiptap/extension-underline'
import { Markdown } from '@tiptap/markdown'
import { Button, Space, Divider, Tooltip } from 'antd'
import {
    BoldOutlined,
    ItalicOutlined,
    UnderlineOutlined,
    StrikethroughOutlined,
    OrderedListOutlined,
    UnorderedListOutlined,
    LinkOutlined,
    CodeOutlined,
    UndoOutlined,
    RedoOutlined,
} from '@ant-design/icons'
import './styles.css'

interface RichTextEditorProps {
    /** Markdown 格式的文本内容 */
    value?: string
    /** 内容变化时回调，返回 Markdown 格式文本 */
    onChange?: (markdown: string) => void
    placeholder?: string
    minHeight?: number
    editable?: boolean
}

const HEADING_LEVELS: Array<1 | 2 | 3> = [1, 2, 3]

export default function RichTextEditor({
    value,
    onChange,
    minHeight = 360,
    editable = true,
}: RichTextEditorProps) {
    // 记录编辑器自身最后一次产出的 markdown，用于区分“外部传入的新 value”
    // 和“编辑器输入触发 onChange 后，父组件把同一份内容传回来”这两种情况，
    // 避免每次按键都被 useEffect 重新 setContent 而打断输入/光标位置。
    const lastEmittedRef = useRef<string | undefined>(value)

    const editor = useEditor({
        extensions: [
            StarterKit,
            Underline,
            Link.configure({ openOnClick: false }),
            Markdown.configure({
                markedOptions: { gfm: true },
            }),
        ],
        content: value || '',
        contentType: 'markdown',
        editable,
        onUpdate: ({ editor: ed }) => {
            const markdown = ed.getMarkdown()
            lastEmittedRef.current = markdown
            onChange?.(markdown)
        },
    })

    useEffect(() => {
        if (editor) {
            editor.setEditable(editable)
        }
    }, [editor, editable])

    // 外部 value 变化时（如切换文档、重置表单）才同步到编辑器；
    // 若这次变化正是编辑器自己刚 emit 出去的内容，则跳过，避免打断输入。
    useEffect(() => {
        if (!editor) return
        if (value === lastEmittedRef.current) return
        const current = editor.getMarkdown()
        if ((value || '') !== current) {
            editor.commands.setContent(value || '', {
                contentType: 'markdown',
            })
        }
        lastEmittedRef.current = value
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [value, editor])

    if (!editor) return null

    return (
        <div
            className="rich-text-editor"
            style={{ border: '1px solid #d9d9d9', borderRadius: 6 }}>
            {editable && (
                <div
                    style={{
                        padding: '6px 8px',
                        borderBottom: '1px solid #d9d9d9',
                        background: '#fafafa',
                    }}>
                    <Space size={4} wrap>
                        {HEADING_LEVELS.map((level) => (
                            <Tooltip title={`标题 ${level}`} key={level}>
                                <Button
                                    size="small"
                                    type={
                                        editor.isActive('heading', { level })
                                            ? 'primary'
                                            : 'text'
                                    }
                                    onClick={() =>
                                        editor
                                            .chain()
                                            .focus()
                                            .toggleHeading({ level })
                                            .run()
                                    }>
                                    H{level}
                                </Button>
                            </Tooltip>
                        ))}
                        <Divider type="vertical" />
                        <Tooltip title="加粗">
                            <Button
                                size="small"
                                type={
                                    editor.isActive('bold')
                                        ? 'primary'
                                        : 'text'
                                }
                                icon={<BoldOutlined />}
                                onClick={() =>
                                    editor.chain().focus().toggleBold().run()
                                }
                            />
                        </Tooltip>
                        <Tooltip title="斜体">
                            <Button
                                size="small"
                                type={
                                    editor.isActive('italic')
                                        ? 'primary'
                                        : 'text'
                                }
                                icon={<ItalicOutlined />}
                                onClick={() =>
                                    editor.chain().focus().toggleItalic().run()
                                }
                            />
                        </Tooltip>
                        <Tooltip title="下划线">
                            <Button
                                size="small"
                                type={
                                    editor.isActive('underline')
                                        ? 'primary'
                                        : 'text'
                                }
                                icon={<UnderlineOutlined />}
                                onClick={() =>
                                    editor
                                        .chain()
                                        .focus()
                                        .toggleUnderline()
                                        .run()
                                }
                            />
                        </Tooltip>
                        <Tooltip title="删除线">
                            <Button
                                size="small"
                                type={
                                    editor.isActive('strike')
                                        ? 'primary'
                                        : 'text'
                                }
                                icon={<StrikethroughOutlined />}
                                onClick={() =>
                                    editor.chain().focus().toggleStrike().run()
                                }
                            />
                        </Tooltip>
                        <Tooltip title="行内代码">
                            <Button
                                size="small"
                                type={
                                    editor.isActive('code')
                                        ? 'primary'
                                        : 'text'
                                }
                                icon={<CodeOutlined />}
                                onClick={() =>
                                    editor.chain().focus().toggleCode().run()
                                }
                            />
                        </Tooltip>
                        <Divider type="vertical" />
                        <Tooltip title="有序列表">
                            <Button
                                size="small"
                                type={
                                    editor.isActive('orderedList')
                                        ? 'primary'
                                        : 'text'
                                }
                                icon={<OrderedListOutlined />}
                                onClick={() =>
                                    editor
                                        .chain()
                                        .focus()
                                        .toggleOrderedList()
                                        .run()
                                }
                            />
                        </Tooltip>
                        <Tooltip title="无序列表">
                            <Button
                                size="small"
                                type={
                                    editor.isActive('bulletList')
                                        ? 'primary'
                                        : 'text'
                                }
                                icon={<UnorderedListOutlined />}
                                onClick={() =>
                                    editor
                                        .chain()
                                        .focus()
                                        .toggleBulletList()
                                        .run()
                                }
                            />
                        </Tooltip>
                        <Tooltip title="链接">
                            <Button
                                size="small"
                                type={
                                    editor.isActive('link')
                                        ? 'primary'
                                        : 'text'
                                }
                                icon={<LinkOutlined />}
                                onClick={() => {
                                    const url = window.prompt('输入链接地址')
                                    if (url) {
                                        editor
                                            .chain()
                                            .focus()
                                            .setLink({ href: url })
                                            .run()
                                    }
                                }}
                            />
                        </Tooltip>
                        <Divider type="vertical" />
                        <Tooltip title="撤销">
                            <Button
                                size="small"
                                icon={<UndoOutlined />}
                                onClick={() => editor.chain().focus().undo().run()}
                            />
                        </Tooltip>
                        <Tooltip title="重做">
                            <Button
                                size="small"
                                icon={<RedoOutlined />}
                                onClick={() => editor.chain().focus().redo().run()}
                            />
                        </Tooltip>
                    </Space>
                </div>
            )}
            <div
                style={{
                    padding: '8px 12px',
                    minHeight,
                    maxHeight: editable ? 520 : undefined,
                    overflow: 'auto',
                }}>
                <EditorContent editor={editor} />
            </div>
        </div>
    )
}
