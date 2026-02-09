import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { AlertCircle, AlertTriangle, Info, XCircle } from "lucide-react";

const severityBadgeVariants = cva(
  "inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium",
  {
    variants: {
      severity: {
        CRITICAL: "bg-destructive/10 text-destructive border border-destructive/20",
        ERROR: "bg-destructive/5 text-destructive",
        WARNING: "bg-warning/10 text-warning",
        INFO: "bg-info/10 text-info",
      },
    },
    defaultVariants: {
      severity: "INFO",
    },
  }
);

const severityIcons = {
  CRITICAL: XCircle,
  ERROR: AlertCircle,
  WARNING: AlertTriangle,
  INFO: Info,
};

export interface SeverityBadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof severityBadgeVariants> {
  severity: 'CRITICAL' | 'ERROR' | 'WARNING' | 'INFO';
  showIcon?: boolean;
}

export function SeverityBadge({ 
  severity, 
  showIcon = true,
  className, 
  children,
  ...props 
}: SeverityBadgeProps) {
  const Icon = severityIcons[severity];
  
  return (
    <span
      className={cn(severityBadgeVariants({ severity }), className)}
      {...props}
    >
      {showIcon && <Icon className="h-3 w-3" />}
      {children || severity}
    </span>
  );
}
