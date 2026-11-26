import React from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "../../theme/ThemeContext";
import { IconButton } from "./Button";

export const ThemeToggle: React.FC<{ className?: string }> = ({ className }) => {
  const { theme, toggleTheme } = useTheme();
  return (
    <IconButton
      label={theme === "dark" ? "Switch to light Sandstone theme" : "Switch to dark Ledger theme"}
      onClick={toggleTheme}
      className={className}
    >
      {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
    </IconButton>
  );
};
