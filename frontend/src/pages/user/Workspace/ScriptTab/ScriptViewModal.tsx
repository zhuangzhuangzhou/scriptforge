import React, { useEffect, useState } from 'react';
import {
  X, ChevronLeft, ChevronRight, Loader2, FileText
} from 'lucide-react';
import { motion } from 'framer-motion';
import { scriptApi } from '../../../../services/api';

interface ScriptContent {
  structure: {
    opening: { content: string; word_count: number };
    development: { content: string; word_count: number };
    climax: { content: string; word_count: number };
    hook: { content: string; word_count: number };
  };
  full_script: string;
  scenes: string[];
  characters: string[];
  hook_type: string;
}

interface ScriptDetail {
  script_id: string;
  project_id: string;
  episode_number: number;
  title: string;
  content: ScriptContent;
  word_count: number;
  scene_count: number;
  qa_status: string | null;
  qa_score: number | null;
  is_current: boolean;
  created_at: string;
}

interface ScriptViewModalProps {
  scriptId: string;
  allScriptIds: string[];
  onClose: () => void;
  onPrevious?: () => void;
  onNext?: () => void;
}

const ScriptViewModal: React.FC<ScriptViewModalProps> = ({
  scriptId,
  allScriptIds,
  onClose,
  onPrevious,
  onNext
}) => {
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState<ScriptDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const currentIndex = allScriptIds.indexOf(scriptId);
  const hasPrevious = currentIndex > 0;
  const hasNext = currentIndex < allScriptIds.length - 1;

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        setLoading(true);
        const response = await scriptApi.getScriptDetail(scriptId);
        setDetail(response.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || '获取剧本详情失败');
      } finally {
        setLoading(false);
      }
    };
    fetchDetail();
  }, [scriptId]);

  const handlePrevious = () => {
    if (hasPrevious && onPrevious) {
      onPrevious();
    }
  };

  const handleNext = () => {
    if (hasNext && onNext) {
      onNext();
    }
  };

  const formatDateTime = (isoString: string | null) => {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN', {
      month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
    });
  };

  const renderSection = (title: string, content: string) => (
    <div className="mb-4">
      <h4 className="text-sm font-semibold text-cyan-400 mb-2">{title}</h4>
      <div className="bg-slate-800/50 rounded-lg p-3 text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
        {content}
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-4xl overflow-hidden shadow-2xl max-h-[90vh] flex flex-col"
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700 shrink-0">
          <div className="flex items-center gap-4">
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-cyan-400" />
              剧本内容
            </h3>
            {detail && (
              <span className="text-xs text-slate-400">
                {allScriptIds.length - currentIndex} / {allScriptIds.length}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* 切换按钮 */}
            <button
              onClick={handlePrevious}
              disabled={!hasPrevious}
              className={`p-1.5 rounded-lg transition-colors ${
                hasPrevious ? 'hover:bg-slate-800 text-slate-300' : 'text-slate-600 cursor-not-allowed'
              }`}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={handleNext}
              disabled={!hasNext}
              className={`p-1.5 rounded-lg transition-colors ${
                hasNext ? 'hover:bg-slate-800 text-slate-300' : 'text-slate-600 cursor-not-allowed'
              }`}
            >
              <ChevronRight className="w-4 h-4" />
            </button>
            <button onClick={onClose} className="p-1.5 hover:bg-slate-800 rounded-lg transition-colors ml-2">
              <X className="w-4 h-4 text-slate-400" />
            </button>
          </div>
        </div>

        {/* 内容 */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
              <p className="text-sm text-slate-400 mt-3">加载中...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-12">
              <X className="w-8 h-8 text-red-400" />
              <p className="text-sm text-red-400 mt-3">{error}</p>
            </div>
          ) : detail ? (
            <div>
              {/* 基本信息 */}
              <div className="mb-4 p-3 bg-slate-800/30 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-lg font-semibold text-white">{detail.title}</h4>
                    <p className="text-xs text-slate-400 mt-1">
                      {formatDateTime(detail.created_at)}
                      {detail.is_current && (
                        <span className="ml-2 text-[10px] px-1.5 py-0.5 bg-cyan-500/20 text-cyan-400 rounded">当前版本</span>
                      )}
                    </p>
                  </div>
                  <div className="flex gap-4 text-xs text-slate-400">
                    <span>字数: {detail.word_count || 0}</span>
                    <span>场景: {detail.scene_count || 0}</span>
                    {detail.qa_score !== null && (
                      <span className={detail.qa_status === 'PASS' ? 'text-green-400' : 'text-red-400'}>
                        质检: {detail.qa_score}
                      </span>
                    )}
                  </div>
                </div>
                {detail.content?.hook_type && (
                  <p className="text-xs text-cyan-400 mt-2">钩子类型: {detail.content.hook_type}</p>
                )}
              </div>

              {/* 四段结构 */}
              {detail.content?.structure && (
                <div>
                  {renderSection('【起】开场冲突', detail.content.structure.opening?.content || '')}
                  {renderSection('【承】推进发展', detail.content.structure.development?.content || '')}
                  {renderSection('【转】反转高潮', detail.content.structure.climax?.content || '')}
                  {renderSection('【钩】悬念结尾', detail.content.structure.hook?.content || '')}
                </div>
              )}

              {/* 角色和场景 */}
              <div className="flex gap-4 mt-4 text-xs">
                {detail.content?.characters && detail.content.characters.length > 0 && (
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500">角色:</span>
                    <div className="flex gap-1">
                      {detail.content.characters.map((char, i) => (
                        <span key={i} className="px-1.5 py-0.5 bg-slate-800 text-slate-300 rounded">
                          {char}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {detail.content?.scenes && detail.content.scenes.length > 0 && (
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500">场景:</span>
                    <div className="flex gap-1 flex-wrap">
                      {detail.content.scenes.map((scene, i) => (
                        <span key={i} className="px-1.5 py-0.5 bg-slate-800 text-slate-300 rounded">
                          {scene}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12">
              <FileText className="w-8 h-8 text-slate-600" />
              <p className="text-sm text-slate-500 mt-3">暂无数据</p>
            </div>
          )}
        </div>

        {/* 底部 */}
        <div className="p-4 border-t border-slate-700 flex justify-end shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded-lg transition-colors"
          >
            关闭
          </button>
        </div>
      </motion.div>
    </div>
  );
};

export default ScriptViewModal;
