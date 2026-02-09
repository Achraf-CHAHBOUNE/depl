import { AlertCircle, HelpCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export type FieldStatus = "ok" | "missing" | "uncertain";

interface FieldStatusIndicatorProps {
  status: FieldStatus;
  fieldName: string;
  className?: string;
}

const statusConfig = {
  missing: {
    badge: "bg-destructive/10 text-destructive border-destructive hover:bg-destructive/20",
    icon: AlertCircle,
    label: "Manquant",
    tooltip: "Ce champ est obligatoire mais n'a pas été rempli ou extrait par l'OCR.",
  },
  uncertain: {
    badge: "bg-warning/10 text-warning border-warning hover:bg-warning/20",
    icon: HelpCircle,
    label: "Incertain",
    tooltip: "Ce champ a été extrait mais nécessite une vérification manuelle.",
  },
  ok: {
    badge: "",
    icon: null,
    label: "",
    tooltip: "",
  },
};

export function FieldStatusIndicator({ 
  status, 
  fieldName,
  className 
}: FieldStatusIndicatorProps) {
  if (status === "ok") return null;
  
  const config = statusConfig[status];
  const Icon = config.icon;
  
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge 
            variant="outline" 
            className={cn(
              "text-xs cursor-help gap-1",
              config.badge,
              className
            )}
          >
            {Icon && <Icon className="h-3 w-3" />}
            {config.label}
          </Badge>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs">
          <p className="text-sm">
            <strong>{fieldName}:</strong> {config.tooltip}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

interface FieldWrapperProps {
  status: FieldStatus;
  children: React.ReactNode;
  className?: string;
}

/**
 * Wraps an input field with a colored border based on status
 */
export function FieldWrapper({ status, children, className }: FieldWrapperProps) {
  return (
    <div 
      className={cn(
        "relative",
        status === "missing" && "[&>input]:border-destructive [&>input]:ring-destructive/20 [&>select]:border-destructive [&>select]:ring-destructive/20",
        status === "uncertain" && "[&>input]:border-warning [&>input]:ring-warning/20 [&>select]:border-warning [&>select]:ring-warning/20",
        className
      )}
    >
      {children}
    </div>
  );
}
