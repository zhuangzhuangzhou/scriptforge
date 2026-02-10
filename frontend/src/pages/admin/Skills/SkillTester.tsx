import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Card, Button, message, Spin, Alert } from 'antd';
import { ArrowLeftOutlined, PlayCircleOutlined } from '@ant-design/icons';
import axios from 'axios';
import MonacoEditor from '@monaco-editor/react';

interface Skill {
  id: string;
  name: string;
  display_name: string;
  description: string;
  example_input: any;
  example_output: any;
}

const SkillTester: React.FC = () => {
  const navigate = useNavigate();
  const { skillId } = useParams<{ skillId: string }>();
  const [skill, setSkill] = useState<Skill | null>(null);
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [inputData, setInputData] = useState('{}');
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [executionTime, setExecutionTime] = useState<number | null>(null);

  // 加载 Skill 数据
  useEffect(() => {
    loadSkill();
  }, [skillId]);

  const loadSkill = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/v1/skills/${skillId}`);
      const skillData = response.data;
      setSkill(skillData);

      // 使用示例输入
      if (skillData.example_input) {
        setInputData(JSON.stringify(skillData.example_input, null, 2));
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  // 执行测试
  const handleTest = async () => {
    setTesting(true);
    setResult(null);
    setError(null);
    setExecutionTime(null);

    try {
      const inputs = JSON.parse(inputData);
      const response = await axios.post(`/api/v1/skills/${skillId}/test`, {
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
      <div className="p-6 flex justify-center items-center h-screen">
        <Spin size="large" />
      </div>
    );
  }

  if (!skill) {
    return (
      <div className="p-6">
        <Alert message="Skill 不存在" type="error" />
      </div>
    );
  }

  return (
    <div className="p-6">
      <Card>
        <div className="mb-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold">{skill.display_name}</h1>
            <p className="text-slate-500">{skill.description}</p>
          </div>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/admin/skills')}
          >
            返回
          </Button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* 输入区域 */}
          <div>
            <div className="mb-2 flex justify-between items-center">
              <h3 className="font-semibold">输入数据 (JSON)</h3>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleTest}
                loading={testing}
              >
                执行测试
              </Button>
            </div>
            <div className="border rounded">
              <MonacoEditor
                height="400px"
                language="json"
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
              <h3 className="font-semibold">执行结果</h3>
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
              <div className="border rounded">
                <MonacoEditor
                  height="400px"
                  language="json"
                  value={JSON.stringify(result, null, 2)}
                  options={{
                    readOnly: true,
                    minimap: { enabled: false },
                    fontSize: 14,
                  }}
                />
              </div>
            ) : (
              <div className="border rounded p-4 h-[400px] flex items-center justify-center text-slate-400">
                点击"执行测试"查看结果
              </div>
            )}
          </div>
        </div>

        {/* 示例输出 */}
        {skill.example_output && (
          <div className="mt-4">
            <h3 className="font-semibold mb-2">预期输出示例</h3>
            <div className="border rounded">
              <MonacoEditor
                height="200px"
                language="json"
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
      </Card>
    </div>
  );
};

export default SkillTester;
