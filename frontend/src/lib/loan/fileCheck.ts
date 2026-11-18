/** LF-005: quick checks before an upload so the user gets a specific message at once. The server
 * still decides (it also checks the file's real content, not just its declared type). */

import type { UploadNotice } from "@/lib/api/types";

export function checkFile(file: File, notice: UploadNotice): string | null {
  if (!notice.allowed_types.includes(file.type)) {
    return `"${file.name}" is not a JPG, PNG or PDF. Choose a photo or PDF of the document.`;
  }
  const limit = notice.max_size_mb * 1024 * 1024;
  if (file.size > limit) {
    const mb = (file.size / (1024 * 1024)).toFixed(1);
    return `"${file.name}" is ${mb} MB, over the ${notice.max_size_mb} MB limit. Choose a smaller file or take the photo at a lower quality.`;
  }
  if (file.size === 0) {
    return `"${file.name}" is empty. Choose a file that has content.`;
  }
  return null;
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
}
