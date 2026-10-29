import os
import logging
from typing import Dict, Any, Optional, List
import msal
import httpx

from app.core.config import settings

logger = logging.getLogger("smartmarks.ms_graph")

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
DEFAULT_SCOPES = ["Files.ReadWrite", "User.Read", "offline_access"]


class MicrosoftGraphService:
    """
    Microsoft Identity (MSAL) and Microsoft Graph integration service.
    Facilitates authorized export of examination workbooks directly into faculty OneDrive.
    """

    def __init__(self):
        self.client_id = os.getenv("AZURE_CLIENT_ID", "")
        self.tenant_id = os.getenv("AZURE_TENANT_ID", "common")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("AZURE_REDIRECT_URI", "http://localhost:5173/auth/callback")
        raw_scopes = os.getenv("AZURE_SCOPES", "")
        self.scopes = [s.strip() for s in raw_scopes.split(",") if s.strip()] if raw_scopes else DEFAULT_SCOPES

    @property
    def is_configured(self) -> bool:
        """Check if Microsoft Azure App credentials have been populated."""
        return bool(
            self.client_id
            and self.client_id != "your_azure_client_id_here"
            and len(self.client_id) > 10
        )

    def _get_authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}"

    def _get_msal_app(self) -> Any:
        if self.client_secret and self.client_secret != "your_azure_client_secret_here":
            return msal.ConfidentialClientApplication(
                client_id=self.client_id,
                client_credential=self.client_secret,
                authority=self._get_authority()
            )
        else:
            return msal.PublicClientApplication(
                client_id=self.client_id,
                authority=self._get_authority()
            )

    def get_auth_url(self, state: Optional[str] = None) -> Dict[str, Any]:
        """Generate Microsoft Identity login redirect URL for faculty sign-in."""
        if not self.is_configured:
            return {
                "configured": False,
                "auth_url": None,
                "message": "Microsoft Azure App Registration not configured in .env. Local XLSX download remains fully active."
            }

        app = self._get_msal_app()
        auth_url = app.get_authorization_request_url(
            scopes=self.scopes,
            redirect_uri=self.redirect_uri,
            state=state or "smartmarks_onedrive_export"
        )
        return {
            "configured": True,
            "auth_url": auth_url,
            "scopes": self.scopes,
            "redirect_uri": self.redirect_uri
        }

    async def acquire_token_by_code(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """Exchange authorization code from Microsoft sign-in for an access token."""
        if not self.is_configured:
            raise RuntimeError("Azure App credentials are not configured in environment.")

        app = self._get_msal_app()
        result = app.acquire_token_by_authorization_code(
            code=code,
            scopes=self.scopes,
            redirect_uri=redirect_uri or self.redirect_uri
        )

        if "error" in result:
            err_msg = result.get("error_description", result.get("error"))
            logger.error("MSAL token acquisition error: %s", err_msg)
            raise RuntimeError(f"Microsoft authentication failed: {err_msg}")

        return {
            "access_token": result["access_token"],
            "token_type": result.get("token_type", "Bearer"),
            "expires_in": result.get("expires_in", 3600),
            "user": result.get("id_token_claims", {}).get("name", "Faculty Member"),
            "email": result.get("id_token_claims", {}).get("preferred_username", "")
        }

    async def upload_workbook_to_onedrive(
        self,
        access_token: str,
        filename: str,
        content_bytes: bytes,
        folder_name: str = "SmartMarks_AI"
    ) -> Dict[str, Any]:
        """
        Upload binary workbook to OneDrive root / folder using Microsoft Graph REST API.
        Endpoint: PUT https://graph.microsoft.com/v1.0/me/drive/root:/{folder_name}/{filename}:/content
        """
        upload_url = f"{GRAPH_API_BASE}/me/drive/root:/{folder_name}/{filename}:/content"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.put(upload_url, headers=headers, content=content_bytes)
            if resp.status_code not in (200, 201):
                logger.error("Microsoft Graph upload error %d: %s", resp.status_code, resp.text)
                raise RuntimeError(
                    f"OneDrive upload failed with status {resp.status_code}: {resp.text}"
                )

            data = resp.json()
            return {
                "success": True,
                "item_id": data.get("id"),
                "filename": data.get("name", filename),
                "web_url": data.get("webUrl"),
                "size_bytes": data.get("size", len(content_bytes)),
                "created_datetime": data.get("createdDateTime"),
                "destination_folder": folder_name
            }


ms_graph_service = MicrosoftGraphService()
