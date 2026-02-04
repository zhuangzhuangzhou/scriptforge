import React, { useState } from 'react';
import { Eye, EyeOff, LucideIcon } from 'lucide-react';
import { motion } from 'framer-motion';

interface InputGroupProps {
  id: string;
  type: string;
  label: string;
  placeholder: string;
  icon: LucideIcon;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

const InputGroup: React.FC<InputGroupProps> = ({
  id,
  type,
  label,
  placeholder,
  icon: Icon,
  value,
  onChange,
}) => {
  const [isFocused, setIsFocused] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const inputType = type === 'password' ? (showPassword ? 'text' : 'password') : type;

  return (
    <div className="w-full space-y-1.5">
      <label htmlFor={id} className="text-xs font-medium text-slate-400 ml-1">
        {label}
      </label>
      <div className="relative group">
        {/* Glow effect on focus */}
        <motion.div
          animate={{ opacity: isFocused ? 1 : 0 }}
          transition={{ duration: 0.2 }}
          className="absolute -inset-0.5 bg-gradient-to-r from-cyan-500 to-blue-600 rounded-lg blur opacity-0 group-hover:opacity-50 transition duration-1000 group-hover:duration-200"
        />
        
        <div className="relative flex items-center bg-slate-900/80 border border-slate-700/50 rounded-lg backdrop-blur-sm overflow-hidden transition-all duration-300 focus-within:border-cyan-500/50 focus-within:ring-1 focus-within:ring-cyan-500/20">
          <div className="pl-3 text-slate-400">
            <Icon size={18} />
          </div>
          <input
            id={id}
            type={inputType}
            value={value}
            onChange={onChange}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={placeholder}
            className="w-full bg-transparent border-none text-sm text-slate-200 placeholder:text-slate-600 px-3 py-3 focus:outline-none focus:ring-0 autofill:bg-transparent"
          />
          {type === 'password' && (
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="pr-3 text-slate-500 hover:text-slate-300 transition-colors focus:outline-none"
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default InputGroup;
