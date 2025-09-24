'use client';

import React, { useState, useEffect } from 'react';
import { StrategyTemplate, StrategyParameter, StrategyConfig } from '@/types';
import { STRATEGY_CATEGORIES } from '@/lib/strategyTemplates';

interface StrategyFormProps {
  onSubmit: (strategy: Partial<StrategyConfig>) => Promise<void>;
  onCancel?: () => void;
  initialValues?: Partial<StrategyConfig>;
  isLoading?: boolean;
  userId?: string;
}

interface FormErrors {
  [key: string]: string;
}

export default function StrategyForm({
  onSubmit,
  onCancel,
  initialValues,
  isLoading = false,
  userId
}: StrategyFormProps) {
  const [templates, setTemplates] = useState<StrategyTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<StrategyTemplate | null>(null);
  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Load strategy templates
  useEffect(() => {
    const loadTemplates = async () => {
      try {
        const response = await fetch('/api/strategies/templates');
        const data = await response.json();
        setTemplates(data.templates || []);
      } catch (error) {
        console.error('Failed to load strategy templates:', error);
      }
    };

    loadTemplates();
  }, []);

  // Initialize form data when template changes
  useEffect(() => {
    if (selectedTemplate) {
      const defaultData = {
        ...selectedTemplate.defaultValues,
        user_id: userId,
        ...initialValues
      };
      setFormData(defaultData);
      setErrors({});
    }
  }, [selectedTemplate, initialValues, userId]);

  // Handle template selection
  const handleTemplateChange = (templateType: string) => {
    const template = templates.find(t => t.type === templateType);
    setSelectedTemplate(template || null);
  };

  // Handle form field changes
  const handleFieldChange = (key: string, value: unknown) => {
    setFormData(prev => ({ ...prev, [key]: value }));

    // Clear error for this field
    if (errors[key]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[key];
        return newErrors;
      });
    }
  };

  // Validate form
  const validateForm = (): boolean => {
    if (!selectedTemplate) {
      setErrors({ template: 'Please select a strategy type' });
      return false;
    }

    const newErrors: FormErrors = {};

    selectedTemplate.parameters.forEach(param => {
      const value = formData[param.key];

      // Required field validation
      if (param.required && (value === undefined || value === null || value === '')) {
        newErrors[param.key] = `${param.label} is required`;
        return;
      }

      // Type-specific validation
      if (value !== undefined && value !== null && value !== '') {
        switch (param.type) {
          case 'number':
            const numValue = typeof value === 'string' ? parseFloat(value) : value;
            if (isNaN(numValue)) {
              newErrors[param.key] = `${param.label} must be a valid number`;
            } else {
              if (param.min !== undefined && numValue < param.min) {
                newErrors[param.key] = `${param.label} must be at least ${param.min}`;
              }
              if (param.max !== undefined && numValue > param.max) {
                newErrors[param.key] = `${param.label} must be at most ${param.max}`;
              }
            }
            break;
          case 'string':
            if (param.validation?.pattern) {
              const regex = new RegExp(param.validation.pattern);
              if (!regex.test(value.toString())) {
                newErrors[param.key] = param.validation.message || `${param.label} format is invalid`;
              }
            }
            break;
        }
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    try {
      // Convert trading_pairs to array if it's a single value
      const submitData = {
        ...formData,
        trading_pairs: Array.isArray(formData.trading_pairs)
          ? formData.trading_pairs
          : [formData.trading_pairs]
      };

      await onSubmit(submitData);
    } catch (error) {
      console.error('Failed to submit strategy:', error);
      setErrors({ submit: 'Failed to create strategy. Please try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Render form field based on parameter type
  const renderField = (param: StrategyParameter) => {
    const value = formData[param.key] || '';
    const hasError = errors[param.key];

    const baseClasses = `w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
      hasError ? 'border-red-500' : 'border-gray-300'
    }`;

    switch (param.type) {
      case 'select':
        return (
          <select
            value={value}
            onChange={(e) => handleFieldChange(param.key, e.target.value)}
            className={baseClasses}
            required={param.required}
          >
            <option value="">Select {param.label}</option>
            {param.options?.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        );

      case 'number':
        return (
          <input
            type="number"
            value={value}
            onChange={(e) => handleFieldChange(param.key, parseFloat(e.target.value) || 0)}
            className={baseClasses}
            min={param.min}
            max={param.max}
            step={param.step}
            required={param.required}
            placeholder={param.default?.toString()}
          />
        );

      case 'boolean':
        return (
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={value === true}
              onChange={(e) => handleFieldChange(param.key, e.target.checked)}
              className="rounded"
            />
            <span className="text-sm text-gray-600">Enable {param.label}</span>
          </div>
        );

      case 'textarea':
        return (
          <textarea
            value={value}
            onChange={(e) => handleFieldChange(param.key, e.target.value)}
            className={baseClasses}
            rows={3}
            required={param.required}
            placeholder={param.description}
          />
        );

      case 'multiselect':
        return (
          <select
            multiple
            value={Array.isArray(value) ? value : [value]}
            onChange={(e) => {
              const selectedValues = Array.from(e.target.selectedOptions, option => option.value);
              handleFieldChange(param.key, selectedValues);
            }}
            className={baseClasses}
            size={Math.min(param.options?.length || 3, 5)}
          >
            {param.options?.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        );

      default:
        return (
          <input
            type="text"
            value={value}
            onChange={(e) => handleFieldChange(param.key, e.target.value)}
            className={baseClasses}
            required={param.required}
            placeholder={param.description}
          />
        );
    }
  };

  // Separate parameters into basic and advanced
  const basicParams = selectedTemplate?.parameters.filter(p =>
    ['name', 'connector_type', 'trading_pairs', 'total_amount_quote', 'order_amount', 'bid_spread', 'ask_spread'].includes(p.key)
  ) || [];

  const advancedParams = selectedTemplate?.parameters.filter(p =>
    !basicParams.some(bp => bp.key === p.key)
  ) || [];

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="mb-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-2">Create New Strategy</h3>
        <p className="text-gray-600">Configure a new trading strategy for your bot</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Strategy Type Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Strategy Type *
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map(template => (
              <div
                key={template.type}
                className={`border-2 rounded-lg p-4 cursor-pointer transition-all hover:shadow-md ${
                  selectedTemplate?.type === template.type
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => handleTemplateChange(template.type)}
              >
                <div className="flex items-center space-x-3">
                  <span className="text-2xl">
                    {STRATEGY_CATEGORIES.find(c => c.value === template.category)?.icon || '📊'}
                  </span>
                  <div>
                    <h4 className="font-medium text-gray-900">{template.name}</h4>
                    <p className="text-sm text-gray-600 mt-1">{template.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
          {errors.template && (
            <p className="text-red-600 text-sm mt-1">{errors.template}</p>
          )}
        </div>

        {/* Strategy Configuration Form */}
        {selectedTemplate && (
          <div className="space-y-6">
            {/* Basic Parameters */}
            <div>
              <h4 className="text-lg font-medium text-gray-900 mb-4">Basic Configuration</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {basicParams.map(param => (
                  <div key={param.key}>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {param.label}
                      {param.required && <span className="text-red-500 ml-1">*</span>}
                    </label>
                    {renderField(param)}
                    {param.description && (
                      <p className="text-xs text-gray-500 mt-1">{param.description}</p>
                    )}
                    {errors[param.key] && (
                      <p className="text-red-600 text-sm mt-1">{errors[param.key]}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Advanced Parameters */}
            {advancedParams.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-lg font-medium text-gray-900">Advanced Configuration</h4>
                  <button
                    type="button"
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                  >
                    {showAdvanced ? 'Hide Advanced' : 'Show Advanced'} ({advancedParams.length} params)
                  </button>
                </div>

                {showAdvanced && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {advancedParams.map(param => (
                      <div key={param.key}>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          {param.label}
                          {param.required && <span className="text-red-500 ml-1">*</span>}
                          {param.tooltip && (
                            <span className="ml-1 text-gray-400 cursor-help" title={param.tooltip}>ⓘ</span>
                          )}
                        </label>
                        {renderField(param)}
                        {param.description && (
                          <p className="text-xs text-gray-500 mt-1">{param.description}</p>
                        )}
                        {errors[param.key] && (
                          <p className="text-red-600 text-sm mt-1">{errors[param.key]}</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Example Configurations */}
            {selectedTemplate.examples && selectedTemplate.examples.length > 0 && (
              <div>
                <h4 className="text-lg font-medium text-gray-900 mb-4">Example Configurations</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {selectedTemplate.examples.map((example, index) => (
                    <div
                      key={index}
                      className="border rounded-lg p-4 cursor-pointer hover:bg-gray-50"
                      onClick={() => {
                        const exampleData = {
                          ...selectedTemplate.defaultValues,
                          ...example.config,
                          user_id: userId
                        };
                        setFormData(exampleData);
                      }}
                    >
                      <h5 className="font-medium text-gray-900">{example.name}</h5>
                      <p className="text-sm text-gray-600 mt-1">{example.description}</p>
                      <p className="text-xs text-blue-600 mt-2">Click to apply</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Form Actions */}
        {selectedTemplate && (
          <div className="flex space-x-4 pt-6 border-t">
            {onCancel && (
              <button
                type="button"
                onClick={onCancel}
                className="px-6 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
                disabled={isSubmitting}
              >
                Cancel
              </button>
            )}
            <button
              type="submit"
              disabled={isSubmitting || isLoading}
              className="flex-1 px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting || isLoading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Creating Strategy...
                </span>
              ) : (
                'Create Strategy'
              )}
            </button>
          </div>
        )}

        {/* Submit Error */}
        {errors.submit && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-red-800">{errors.submit}</p>
          </div>
        )}
      </form>
    </div>
  );
}
