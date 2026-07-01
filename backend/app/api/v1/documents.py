"""文档管理 API 路由."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.document import DocumentType, DocumentStatus
from app.schemas.document import (
    DocumentCreate,
    DocumentDetailResponse,
    DocumentResponse,
    DocumentUpdate,
    DocumentVersionResponse,
)
from app.services.document_service import DocumentService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/documents", tags=["文档管理"])


def _doc_response(doc, author_name: str | None = None) -> DocumentResponse:
    """Build DocumentResponse from ORM model."""
    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        doc_type=doc.doc_type,
        doc_number=doc.doc_number,
        status=doc.status,
        version=doc.version,
        summary=doc.summary,
        system_name=doc.system_name,
        project_id=doc.project_id,
        author_id=doc.author_id,
        author_name=author_name or (doc.author.full_name if doc.author else None),
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.post("", response_model=DocumentResponse)
async def create_document(
    data: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建新文档."""
    service = DocumentService(db)
    doc = await service.create_document(data, author_id=current_user.id)
    return _doc_response(doc, author_name=current_user.full_name)


@router.get("", response_model=dict)
async def list_documents(
    doc_type: DocumentType | None = None,
    status: DocumentStatus | None = None,
    system_name: str | None = None,
    keyword: str | None = None,
    project_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """获取文档列表."""
    service = DocumentService(db)
    documents, total = await service.list_documents(
        doc_type=doc_type,
        status=status,
        system_name=system_name,
        keyword=keyword,
        project_id=project_id,
        page=page,
        page_size=page_size,
    )
    return {
        "items": [_doc_response(doc) for doc in documents],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """获取文档详情."""
    service = DocumentService(db)
    doc = await service.get_document(document_id)
    versions = await service.get_versions(document_id)
    return DocumentDetailResponse(
        **_doc_response(doc).model_dump(),
        content=doc.content,
        versions=[DocumentVersionResponse.model_validate(v) for v in versions],
    )


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新文档."""
    service = DocumentService(db)
    # 先获取旧值用于审计
    old_doc = await service.get_document(document_id)
    old_values = {
        "title": old_doc.title,
        "content": old_doc.content,
        "summary": old_doc.summary,
        "system_name": old_doc.system_name,
    }

    doc = await service.update_document(document_id, data, current_user.id)

    # 记录审计日志 - 每个变更字段一条
    audit = AuditService(db)
    field_map = {
        "title": ("title", data.title),
        "content": ("content", data.content),
        "summary": ("summary", data.summary),
        "system_name": ("system_name", data.system_name),
    }
    for field, (field_name, new_val) in field_map.items():
        if new_val is not None and new_val != old_values[field]:
            await audit.log(
                action="UPDATE",
                resource_type="document",
                user_id=current_user.id,
                username=current_user.username,
                resource_id=document_id,
                resource_name=doc.title,
                field_changed=field_name,
                old_value=old_values[field],
                new_value=new_val,
            )

    return _doc_response(doc)


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除文档."""
    service = DocumentService(db)
    await service.delete_document(document_id, current_user.id)
    return {"message": "文档已删除"}


@router.get("/{document_id}/versions", response_model=list[DocumentVersionResponse])
async def get_document_versions(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """获取文档版本历史."""
    service = DocumentService(db)
    versions = await service.get_versions(document_id)
    return [DocumentVersionResponse.model_validate(v) for v in versions]
