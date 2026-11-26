import React from "react";
import { StatusPill } from "./ui/Badge";

export const StatusBadge: React.FC<{ value: string }> = ({ value }) => (
  <StatusPill value={value} />
);
