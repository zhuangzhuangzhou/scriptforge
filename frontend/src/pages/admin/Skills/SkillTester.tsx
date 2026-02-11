import React, { useState, useEffect } from 'react';
import { Button, message, Spin, Alert } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import MonacoEditor from '@monaco-editor/react';
import api from '../../../services/api';

interface Skill {
  id: string;
  name: string;
  display_name: string;
  description: string;
  example_input: any;
  example_output: any;
}

interface SkillTesterProps {
  skillId: string;
}

const SkillTester: React.FC<SkillTesterProps> = ({ skillId }) => {
  const [skill, setSkill] = useState<Skill | null>(null);
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [inputData, setInputData] = useState('{}');
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [executionTime, setExecutionTime] = useState<number | null>(null);

  useEffect(() => {
    loadSkill();
  }, [skillId]);

  const loadSkill = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/skills/${skillId}`);
      const skillData = response.data;
      setSkill(skillData);

      if (skillData.example_input) {
        setInputData(JSON.stringify(skillData.example_input, null, 2));
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setResult(null);
    setError(null);
    setExecutionTime(null);

    try {
      const inputs = JSON.parse(inputData);
      const response = await api.post(`/skills/${skillId}/test`, {
        inputs,
      });

      if (response.data.success) {
        setResult(response.data.result);
        setExecutionTime(response.data.execution_time);
        message.success('测试成功');
      } else {
        setError(response.data.error);
        message.error('测试失败');
      }
    } catch (error: any) {
      setError(error.response?.data?.detail || error.message);
      message.error('测试失败');
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <Spin size="large" />
      </div>
    );
  }

  if (!skill) {
    return <Alert message="Skill 不存在" type="error" />;
  }

  return (
    <div>
      <div className="mb-4">
        <p className="text-slate-400">{skill.description}</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* 输入区域 */}
        <div>
          <div className="mb-2 flex justify-between items-center">
            <h3 className="font-semibold text-slate-200">输入数据 (JSON)</h3>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleTest}
              loading={testing}
            >
              执行测试
            </Button>
          </div>
          <div className="border border-slate-700 rounded">
            <MonacoEditor
              height="350px"
              language="json"
              theme="vs-dark"
              value={inputData}
              onChange={(value) => setInputData(value || '{}')}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
              }}
            />
          </div>
        </div>

        {/* 输出区域 */}
        <div>
          <div className="mb-2 flex justify-between items-center">
            <h3 className="font-semibold text-slate-200">执行结果</h3>
            {executionTime !== null && (
              <span className="text-sm text-slate-500">
                耗时: {executionTime.toFixed(2)}s
              </span>
            )}
          </div>

          {error ? (
            <Alert
              message="执行失败"
              description={error}
              type="error"
              showIcon
            />
          ) : result ? (
            <div className="border border-slate-700 rounded">
              <MonacoEditor
                height="350px"
                language="json"
                theme="vs-dark"
                value={JSON.stringify(result, null, 2)}
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  fontSize: 14,
                }}
              />
            </div>
          ) : (
            <div className="border border-slate-700 rounded p-4 h-[350px] flex items-center justify-center text-slate-400">
              点击"执行测试"查看结果
            </div>
          )}
        </div>
      </div>

      {/* 示例输出 */}
      {skill.example_output && (
        <div className="mt-4">
          <h3 className="font-semibold mb-2 text-slate-200">预期输出示例</h3>
          <div className="border border-slate-700 rounded">
            <MonacoEditor
              height="150px"
              language="json"
              theme="vs-dark"
              value={JSON.stringify(skill.example_output, null, 2)}
              options={{
                readOnly: true,
                minimap: { enabled: false },
                fontSize: 14,
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default SkillTester;
