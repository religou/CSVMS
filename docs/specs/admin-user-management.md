# Spec: 管理员用户管理界面完善

## Objective

管理员角色（admin）在用户管理界面应可以对所有用户执行完整的 CRUD 和管理操作，包括编辑信息、分配角色、重置密码、删除用户。当前前端仅实现了部分功能（创建、启用/禁用、解锁），需要补齐剩余操作的 UI 及对应后端 API。

### 用户故事

- 作为管理员，我可以编辑任何用户的姓名和邮箱
- 作为管理员，我可以为任何用户分配或修改角色
- 作为管理员，我可以重置任何用户的密码（设置新密码）
- 作为管理员，我可以删除不再需要的用户（硬删除）
- 作为管理员，我不能禁用/锁定/删除自己的账户（自保护机制）

## Commands

```bash
# 后端测试
Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/ -v; Pop-Location

# 后端启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir c:\Users\zhouek\Work\SelfProject\CSVS\backend

# 前端开发
cd frontend; npm run dev
```

## 现有状态

### 后端 API（已有）

| 端点                       | 方法 | 功能     | 权限                    |
| -------------------------- | ---- | -------- | ----------------------- |
| `/admin/users`             | GET  | 用户列表 | admin, validation_admin |
| `/admin/users`             | POST | 创建用户 | admin                   |
| `/admin/users/{id}`        | PUT  | 更新用户 | admin                   |
| `/admin/users/{id}/roles`  | POST | 分配角色 | admin                   |
| `/admin/users/{id}/unlock` | POST | 解锁用户 | admin                   |

### 后端 API（需新增）

| 端点                               | 方法   | 功能     | 权限  |
| ---------------------------------- | ------ | -------- | ----- |
| `/admin/users/{id}/reset-password` | POST   | 重置密码 | admin |
| `/admin/users/{id}`                | DELETE | 删除用户 | admin |

### 前端（已有）

- 用户列表表格
- 创建用户弹窗
- 启用/禁用切换
- 解锁按钮

### 前端（需新增）

- 编辑用户弹窗（修改姓名、邮箱）
- 角色分配弹窗（多选角色）
- 重置密码弹窗（输入新密码）
- 删除按钮（带二次确认）
- 自保护逻辑：操作按钮对当前登录用户禁用

## Code Style

遵循现有代码风格：

```tsx
// 前端组件风格 - 使用 Ant Design Modal + Form
const handleEdit = async (values: EditFormValues) => {
    try {
        await adminService.updateUser(userId, values)
        message.success('更新成功')
        setEditModalOpen(false)
        fetchUsers()
    } catch (err: unknown) {
        const error = err as { response?: { data?: { detail?: string } } }
        message.error(error.response?.data?.detail || '更新失败')
    }
}
```

```python
# 后端 API 风格 - FastAPI + SQLAlchemy async
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_roles("admin")),
):
    """删除用户."""
    if user_id == current_user.id:
        raise BusinessError("不能删除自己的账户")
    ...
```

## Testing Strategy

- **后端**: pytest + aiosqlite，测试文件位于 `backend/tests/`
- **前端**: 暂无单元测试框架配置（本次不增加）
- 覆盖场景:
    - 重置密码 API 正常/异常
    - 删除用户 API 正常/异常/自删除保护
    - 自保护逻辑（禁止操作自己）

## Boundaries

- **Always**:
    - 删除操作需二次确认（前端 Modal.confirm）
    - 后端校验自保护逻辑（不依赖前端）
    - 密码重置后记录审计日志
    - API 返回合适的错误码和中文提示

- **Ask first**:
    - 是否需要邮件通知被重置密码的用户
    - 删除用户时关联数据的处理策略

- **Never**:
    - 不在前端存储/展示用户密码
    - 不允许硬编码跳过权限检查
    - 不删除有审计日志引用的用户（如需要后续可改为软删除）

## Success Criteria

1. 管理员可在用户列表中点击「编辑」打开弹窗修改用户姓名和邮箱
2. 管理员可在用户列表中点击「角色」打开弹窗重新分配角色
3. 管理员可在用户列表中点击「重置密码」设置新密码
4. 管理员可在用户列表中点击「删除」并经二次确认后删除用户
5. 当前登录管理员的行不显示「禁用」「删除」按钮（或按钮禁用状态）
6. 后端 API 拒绝管理员禁用/删除自己并返回明确错误信息
7. 所有新增后端 API 有对应的测试用例通过

## Open Questions

1. 删除用户时，如果该用户有关联的文档/审批记录，是否阻止删除还是级联处理？阻止删除并提示
2. 重置密码后是否需要强制用户下次登录时修改密码？不需要，重置密码可以邮件提醒用户
