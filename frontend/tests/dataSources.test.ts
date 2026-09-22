import { describe, it, expect } from 'vitest';
import { CreateDataSourceDTO, DataSourceType } from '../src/api/types';
import { MIME_OPTIONS } from '../src/components/data-sources/MimeTypeSelector';

describe('Data Sources Configuration & Helpers', () => {
  const cleanFolderId = (raw: string): string => {
    const trimmed = raw.trim();
    const urlMatch = trimmed.match(/\/folders\/([a-zA-Z0-9_-]+)/);
    if (urlMatch) return urlMatch[1];
    return trimmed;
  };

  const isValidFolderId = (folderId: string): boolean => {
    return /^(root|[a-zA-Z0-9_-]+)$/.test(folderId);
  };

  it('extracts folder ID from a full Google Drive URL', () => {
    const url =
      'https://drive.google.com/drive/folders/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs?usp=sharing';
    expect(cleanFolderId(url)).toBe('1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs');
  });

  it('preserves clean folder IDs entered directly', () => {
    const id = '1aBcDeFgHiJkLmNoP_012-xyz';
    expect(cleanFolderId(id)).toBe('1aBcDeFgHiJkLmNoP_012-xyz');
  });

  it('accepts root as valid folder ID', () => {
    expect(isValidFolderId('root')).toBe(true);
    expect(isValidFolderId('1234_abcd-EFGH')).toBe(true);
  });

  it('rejects malicious or injection folder IDs', () => {
    expect(isValidFolderId("root' or '1'='1")).toBe(false);
    expect(isValidFolderId('../../etc/passwd')).toBe(false);
    expect(isValidFolderId('folder; rm -rf /')).toBe(false);
    expect(isValidFolderId('')).toBe(false);
  });

  it('constructs a compliant CreateDataSourceDTO payload', () => {
    const payload: CreateDataSourceDTO = {
      name: 'Google Drive Jurídico',
      data_source_type: 'google_drive_folder' as DataSourceType,
      sync_interval_minutes: 15,
      config: {
        folder_id: '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs',
        recursive: true,
        baseline_days: 30,
        include_mime_types: [
          'application/pdf',
          'application/vnd.google-apps.document',
        ],
      },
    };

    expect(payload.name).toBe('Google Drive Jurídico');
    expect(payload.data_source_type).toBe('google_drive_folder');
    expect(payload.sync_interval_minutes).toBe(15);
    expect((payload.config as { folder_id: string }).folder_id).toBe(
      '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs'
    );
  });

  it('includes standard MIME options including PDF and Google Docs', () => {
    const mimes = MIME_OPTIONS.map((m) => m.mime);
    expect(mimes).toContain('application/pdf');
    expect(mimes).toContain('application/vnd.google-apps.document');
    expect(mimes).toContain('application/vnd.google-apps.spreadsheet');
    expect(mimes).toContain('text/markdown');
    expect(mimes).toContain('audio/mpeg');
  });
});
