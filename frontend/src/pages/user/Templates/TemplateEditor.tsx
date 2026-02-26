import React, { useState, useEffect } from 'react';
import { message, Spin } from 'antd';
import { ArrowLeft, Save, FileText, Tag, Eye, EyeOff } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../../services/api';
import { GlassCard } from '../../../components/ui/GlassCard';
import { GlassInput, GlassTextArea } from '../../../components/ui/GlassInput';
import { GlassSelect } from '../../../components/ui/GlassSelect';
import MarkdownEditor from '../../../components/MarkdownEditor';

const categoryOptions = [
  { value: 'methodology', label: '方法论' },
  { value: 'output_style', label: '输出风格' },
  { value: 'qa_rules', label: '质检标准' },
  { value: 'template', label: '模板案例' },
  { value: 'breakdown_prompt', label: '拆解提示词' },
];

const visibilityOptions = [
  { value: 'private', label: '仅自己可见' },
  { value: 'public', label: '公开（其他用户可复制）' },
];

const TemplateEditor: React.FC = () => {
  const { templateId } = useParams<{ templateId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // 表单数据
  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    description: '',
    category: 'methodology',
    visibility: 'private',
  });
  const [content, setContent] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const isEditMode = !!templateId;

  useEffect(() => {
    if (isEditMode) {
      loadTemplate();
    }
  }, [templateId]);

  const loadTemplate = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/ai-resources/${templateId}`);
      const resource = response.data;

      if (resource.is_builtin) {
        message.warning('内置模板不能直接编辑，请先复制为自己的版本');
        navigate('/user/templates');
        return;
      }

      setFormData({
        name: resource.name,
        display_name: resource.display_name,
        description: resource.description || '',
        category: resource.category,
        visibility: resource.visibility,
      });
      setContent(resource.content || '');
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '加载失败');
      navigate('/user/templates');
    } finally {
      setLoading(false);
    }
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = '请输入模板名称';
    } else if (!/^[a-z0-9_]+$/.test(formData.name)) {
      newErrors.name = '只能包含小写字母、数字和下划线';
    }

    if (!formData.display_name.trim()) {
      newErrors.display_name = '请输入显示名称';
    }

    if (!content.trim()) {
      newErrors.content = '请输入模板内容';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validate()) return;

    setSaving(true);
    try {
      const data = { ...formData, content };

      if (isEditMode) {
        await api.put(`/ai-resources/${templateId}`, data);
        message.success('保存成功');
      } else {
        await api.post('/ai-resources', data);
        message.success('创建成功');
      }

      navigate('/user/templates');
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleFieldChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-full bg-slate-950">
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-slate-950 p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* 顶部标题栏 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/user/templates')}
              className="p-2 rounded-lg bg-slate-800/50 border border-slate-700 text-slate-400 hover:text-white hover:border-slate-600 transition-all"
            >
              <ArrowLeft size={20} />
            </button>
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2">
                <FileText size={20} className="text-indigo-400" />
                {isEditMode ? '编辑模板' : '新建模板'}
              </h1>
              <p className="text-xs text-slate-500 mt-1">
                {isEditMode ? '修改模板内容和配置' : '创建自定义提示词模板'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/user/templates')}
              className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-5 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-lg font-medium flex items-center gap-2 transition-all disabled:opacity-50"
            >
              <Save size={16} />
              {saving ? '保存中...' : '保存'}
            </button>
          </div>
        </div>

        {/* 基础信息卡片 */}
        <GlassCard>
          <h2 className="text-sm font-bold text-white mb-4 flex items-center gap-2 border-b border-slate-800 pb-3">
            <Tag size={14} className="text-cyan-400" />
            基础信息
          </h2>

          <div className="grid grid-cols-2 gap-6">
            {/* 模板名称 */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                模板名称 <span className="text-red-400">*</span>
              </label>
              <GlassInput
                value={formData.name}
                onChange={(e) => handleFieldChange('name', e.target.value)}
                placeholder="例如：my_adapt_method"
                disabled={isEditMode}
                status={errors.name ? 'error' : undefined}
              />
              {errors.name ? (
                <p className="text-xs text-red-400">{errors.name}</p>
              ) : (
                <p className="text-[10px] text-slate-500">唯一标识，只能包含小写字母、数字和下划线</p>
              )}
            </div>

            {/* 显示名称 */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                显示名称 <span className="text-red-400">*</span>
              </label>
              <GlassInput
                value={formData.display_name}
                onChange={(e) => handleFieldChange('display_name', e.target.value)}
                placeholder="例如：我的改编方法论"
                status={errors.display_name ? 'error' : undefined}
              />
              {errors.display_name && (
                <p className="text-xs text-red-400">{errors.display_name}</p>
              )}
            </div>
          </div>

          {/* 描述 */}
          <div className="mt-4 space-y-2">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              描述
            </label>
            <GlassTextArea
              value={formData.description}
              onChange={(e) => handleFieldChange('description', e.target.value)}
              rows={2}
              placeholder="简要描述此模板的用途和特点"
            />
          </div>

          <div className="grid grid-cols-2 gap-6 mt-4">
            {/* 分类 */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                分类 <span className="text-red-400">*</span>
              </label>
              <GlassSelect
                value={formData.category}
                onChange={(value) => handleFieldChange('category', value)}
                options={categoryOptions}
                disabled={isEditMode}
                className="w-full"
              />
            </div>

            {/* 可见性 */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                可见性
                {formData.visibility === 'private' ? (
                  <EyeOff size={12} className="text-slate-500" />
                ) : (
                  <Eye size={12} className="text-emerald-400" />
                )}
              </label>
              <GlassSelect
                value={formData.visibility}
                onChange={(value) => handleFieldChange('visibility', value)}
                options={visibilityOptions}
                className="w-full"
              />
            </div>
          </div>
        </GlassCard>

        {/* 模板内容卡片 */}
        <GlassCard>
          <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <FileText size={14} className="text-purple-400" />
              模板内容 <span className="text-red-400">*</span>
            </h2>
            {formData.category === 'breakdown_prompt' && (
              <div className="text-[10px] text-slate-500 bg-slate-800/50 px-3 py-1 rounded-full">
                可用变量: {'{{chapters_text}}'}, {'{{novel_type}}'}
              </div>
            )}
          </div>

          {errors.content && (
            <p className="text-xs text-red-400 mb-2">{errors.content}</p>
          )}

          <MarkdownEditor
            value={content}
            onChange={setContent}
            height="450px"
            showVariables={true}
          />
        </GlassCard>
      </div>
    </div>
  );
};

export default TemplateEditor;
