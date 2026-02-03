import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface CreateProjectForm {
  name: string;
  novel_type: string;
  description: string;
  batch_size: number;
  chapter_split_rule: string;
}

const CreateProject: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState<CreateProjectForm>({
    name: '',
    novel_type: '都市',
    description: '',
    batch_size: 5,
    chapter_split_rule: 'auto'
  });
  const [file, setFile] = useState<File | null>(null);

  const novelTypes = ['都市', '古装', '科幻', '玄幻', '武侠', '言情', '悬疑', '其他'];
  const splitRules = [
    { value: 'auto', label: '自动识别（第X章、Chapter等）' },
    { value: 'blank_line', label: '空行分隔' },
    { value: 'custom', label: '自定义规则' }
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!form.name || !file) {
      alert('请填写项目名称并上传文件');
      return;
    }

    setLoading(true);
    try {
      // 1. 创建项目
      const projectResponse = await fetch('/api/v1/projects', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(form)
      });

      if (!projectResponse.ok) throw new Error('创建项目失败');
      const project = await projectResponse.json();

      // 2. 上传文件
      const formData = new FormData();
      formData.append('file', file);

      const uploadResponse = await fetch(`/api/v1/projects/${project.id}/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: formData
      });

      if (!uploadResponse.ok) throw new Error('上传文件失败');

      alert('项目创建成功！');
      navigate('/dashboard');
    } catch (error) {
      alert(error instanceof Error ? error.message : '操作失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-3xl mx-auto px-4">
        <div className="bg-white rounded-lg shadow p-6">
          <h1 className="text-2xl font-bold mb-6">创建新项目</h1>

          {/* 项目基础信息 */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                项目名称 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="请输入项目名称"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                小说类型 <span className="text-red-500">*</span>
              </label>
              <select
                value={form.novel_type}
                onChange={(e) => setForm({ ...form, novel_type: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {novelTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                项目描述
              </label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="请输入项目描述（可选）"
              />
            </div>
          </div>

          {/* 批次配置 */}
          <div className="mt-6 pt-6 border-t border-gray-200">
            <h2 className="text-lg font-semibold mb-4">批次配置</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  批次大小 <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  min="1"
                  max="20"
                  value={form.batch_size}
                  onChange={(e) => setForm({ ...form, batch_size: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="mt-1 text-sm text-gray-500">
                  每个批次包含的章节数，建议5-10章
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  章节拆分规则 <span className="text-red-500">*</span>
                </label>
                <select
                  value={form.chapter_split_rule}
                  onChange={(e) => setForm({ ...form, chapter_split_rule: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {splitRules.map(rule => (
                    <option key={rule.value} value={rule.value}>{rule.label}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* 文件上传 */}
          <div className="mt-6 pt-6 border-t border-gray-200">
            <h2 className="text-lg font-semibold mb-4">上传小说文件</h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                选择文件 <span className="text-red-500">*</span>
              </label>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                <input
                  type="file"
                  accept=".txt,.docx,.pdf"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="hidden"
                  id="file-upload"
                />
                <label htmlFor="file-upload" className="cursor-pointer">
                  <div className="text-gray-600">
                    {file ? (
                      <div>
                        <p className="font-medium">{file.name}</p>
                        <p className="text-sm text-gray-500 mt-1">
                          {(file.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                    ) : (
                      <div>
                        <p>点击或拖拽文件到此处上传</p>
                        <p className="text-sm text-gray-500 mt-1">
                          支持 .txt, .docx, .pdf 格式，最大 50MB
                        </p>
                      </div>
                    )}
                  </div>
                </label>
              </div>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="mt-6 pt-6 border-t border-gray-200 flex justify-end space-x-4">
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className="px-6 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              disabled={loading}
            >
              取消
            </button>
            <button
              type="submit"
              onClick={handleSubmit}
              disabled={loading || !form.name || !file}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {loading ? '创建中...' : '创建项目'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CreateProject;
