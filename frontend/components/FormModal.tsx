'use client';

import { useState, useEffect } from 'react';
import { X, Check, Copy, AlertCircle } from 'lucide-react';
import { copyToClipboard } from '@/lib/utils';

// Field configuration type
export interface FormField {
  name: string;
  label: string;
  type: 'text' | 'number' | 'email' | 'password' | 'select' | 'textarea' | 'checkbox';
  placeholder?: string;
  required?: boolean;
  default?: any;
  options?: { label: string; value: string | number }[] | string[];
  min?: number;
  max?: number;
  rows?: number;
  disabled?: boolean;
  helpText?: string;
}

// Success display configuration
export interface SuccessConfig {
  title: string;
  message?: string;
  highlightField?: string;
  highlightLabel?: string;
  copyable?: boolean;
  viewLink?: {
    label: string;
    href: (data: any) => string;
  };
}

interface FormModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  fields: FormField[];
  submitLabel?: string;
  onSubmit: (data: Record<string, any>) => Promise<any>;
  onSuccess?: (result: any) => void;
  successConfig?: SuccessConfig;
  size?: 'sm' | 'md' | 'lg';
}

export default function FormModal({
  isOpen,
  onClose,
  title,
  subtitle,
  fields,
  submitLabel = 'Submit',
  onSubmit,
  onSuccess,
  successConfig,
  size = 'md',
}: FormModalProps) {
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [copied, setCopied] = useState(false);

  // Initialize form data with defaults
  useEffect(() => {
    if (isOpen) {
      const initialData: Record<string, any> = {};
      fields.forEach((field) => {
        if (field.default !== undefined) {
          initialData[field.name] = field.default;
        } else if (field.type === 'checkbox') {
          initialData[field.name] = false;
        } else if (field.type === 'number') {
          initialData[field.name] = 0;
        } else {
          initialData[field.name] = '';
        }
      });
      setFormData(initialData);
      setError('');
      setSuccess(false);
      setResult(null);
    }
  }, [isOpen, fields]);

  const sizeStyles = {
    sm: '380px',
    md: '480px',
    lg: '600px',
  };

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await onSubmit(formData);
      setResult(response);
      setSuccess(true);
      if (onSuccess) onSuccess(response);
    } catch (err: any) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  function handleClose() {
    setFormData({});
    setError('');
    setSuccess(false);
    setResult(null);
    setCopied(false);
    onClose();
  }

  function handleCopy(text: string) {
    copyToClipboard(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleChange(name: string, value: any) {
    setFormData((prev) => ({ ...prev, [name]: value }));
  }

  function getNestedValue(obj: any, path: string) {
    return path.split('.').reduce((acc, part) => acc?.[part], obj);
  }

  function renderField(field: FormField) {
    const value = formData[field.name] ?? '';

    const baseInputStyle = {
      width: '100%',
      padding: '10px 14px',
      borderRadius: '8px',
      backgroundColor: 'var(--bg-tertiary)',
      border: '1px solid var(--border-subtle)',
      color: 'var(--text-primary)',
      fontSize: '14px',
      transition: 'all 0.2s',
    };

    switch (field.type) {
      case 'select':
        return (
          <select
            value={value}
            onChange={(e) => handleChange(field.name, e.target.value)}
            disabled={field.disabled}
            style={{ ...baseInputStyle, cursor: 'pointer' }}
          >
            {field.options?.map((opt) => {
              const optValue = typeof opt === 'string' ? opt : opt.value;
              const optLabel = typeof opt === 'string' ? opt.charAt(0).toUpperCase() + opt.slice(1) : opt.label;
              return (
                <option key={optValue} value={optValue}>
                  {optLabel}
                </option>
              );
            })}
          </select>
        );

      case 'textarea':
        return (
          <textarea
            value={value}
            onChange={(e) => handleChange(field.name, e.target.value)}
            placeholder={field.placeholder}
            required={field.required}
            disabled={field.disabled}
            rows={field.rows || 3}
            style={{ ...baseInputStyle, resize: 'none' }}
          />
        );

      case 'checkbox':
        return (
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={value}
              onChange={(e) => handleChange(field.name, e.target.checked)}
              disabled={field.disabled}
              style={{ width: '18px', height: '18px', cursor: 'pointer' }}
            />
            <span style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>{field.placeholder || field.label}</span>
          </label>
        );

      case 'number':
        return (
          <input
            type="number"
            value={value}
            onChange={(e) => handleChange(field.name, parseInt(e.target.value) || 0)}
            placeholder={field.placeholder}
            required={field.required}
            disabled={field.disabled}
            min={field.min}
            max={field.max}
            style={baseInputStyle}
          />
        );

      default:
        return (
          <input
            type={field.type}
            value={value}
            onChange={(e) => handleChange(field.name, e.target.value)}
            placeholder={field.placeholder}
            required={field.required}
            disabled={field.disabled}
            style={baseInputStyle}
          />
        );
    }
  }

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div
        className="modal-content"
        style={{maxWidth: sizeStyles[size],
                maxHeight: '90vh',  
                overflowY: 'auto'    }}


        onClick={(e) => e.stopPropagation()}
      >
        {success && successConfig ? (
          // Success State
          <div style={{ textAlign: 'center' }}>
            <div
              style={{
                width: '64px',
                height: '64px',
                margin: '0 auto 16px',
                borderRadius: '50%',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Check size={32} color="#059669" />
            </div>
            <h3 style={{ fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '8px' }}>
              {successConfig.title}
            </h3>
            {successConfig.message && (
              <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>{successConfig.message}</p>
            )}

            {successConfig.highlightField && (
              <div
                style={{
                  backgroundColor: 'var(--bg-tertiary)',
                  padding: '16px',
                  borderRadius: '12px',
                  marginBottom: '24px',
                }}
              >
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  {successConfig.highlightLabel || successConfig.highlightField}
                </p>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px' }}>
                  <code
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: '18px',
                      color: '#4f46e5',
                      fontWeight: 600,
                    }}
                  >
                    {getNestedValue(result, successConfig.highlightField)}
                  </code>
                  {successConfig.copyable && (
                    <button
                      onClick={() => handleCopy(getNestedValue(result, successConfig.highlightField))}
                      style={{
                        padding: '8px',
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        borderRadius: '8px',
                      }}
                    >
                      {copied ? <Check size={20} color="#059669" /> : <Copy size={20} color="var(--text-muted)" />}
                    </button>
                  )}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', gap: '12px' }}>
              <button onClick={handleClose} className="btn btn-secondary" style={{ flex: 1 }}>
                Close
              </button>
              {successConfig.viewLink && (
                <a
                  href={successConfig.viewLink.href(result)}
                  className="btn btn-primary"
                  style={{ flex: 1, textAlign: 'center', textDecoration: 'none' }}
                >
                  {successConfig.viewLink.label}
                </a>
              )}
            </div>
          </div>
        ) : (
          // Form State
          <>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '24px',
              }}
            >
              <div>
                <h2 style={{ fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)' }}>{title}</h2>
                {subtitle && (
                  <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginTop: '4px' }}>{subtitle}</p>
                )}
              </div>
              <button
                onClick={handleClose}
                style={{
                  padding: '8px',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  borderRadius: '8px',
                }}
              >
                <X size={20} color="var(--text-muted)" />
              </button>
            </div>

            {error && (
              <div
                style={{
                  marginBottom: '16px',
                  padding: '12px',
                  borderRadius: '8px',
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  color: '#dc2626',
                  fontSize: '14px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <AlertCircle size={18} />
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {fields.map((field) => (
                <div key={field.name}>
                  {field.type !== 'checkbox' && (
                    <label
                      style={{
                        display: 'block',
                        fontSize: '14px',
                        fontWeight: 500,
                        color: 'var(--text-secondary)',
                        marginBottom: '6px',
                      }}
                    >
                      {field.label}
                      {field.required && <span style={{ color: '#dc2626', marginLeft: '4px' }}>*</span>}
                    </label>
                  )}
                  {renderField(field)}
                  {field.helpText && (
                    <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>{field.helpText}</p>
                  )}
                </div>
              ))}

              <div style={{ display: 'flex', gap: '12px', paddingTop: '8px' }}>
                <button type="button" onClick={handleClose} className="btn btn-secondary" style={{ flex: 1 }}>
                  Cancel
                </button>
                <button type="submit" disabled={loading} className="btn btn-primary" style={{ flex: 1 }}>
                  {loading ? 'Processing...' : submitLabel}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
}