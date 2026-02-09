import { Clock, User } from "lucide-react";
import { cn } from "@/lib/utils";
import { AuditEntry } from "@/types";
import { format } from "date-fns";

interface AuditTimelineProps {
  entries: AuditEntry[];
  className?: string;
}

export function AuditTimeline({ entries, className }: AuditTimelineProps) {
  return (
    <div className={cn("space-y-4", className)}>
      <h4 className="font-medium text-foreground">Audit Trail</h4>
      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-3 top-0 bottom-0 w-px bg-border" />
        
        <div className="space-y-4">
          {entries.map((entry, index) => (
            <div key={entry.id} className="relative flex gap-4 pl-8">
              {/* Timeline dot */}
              <div 
                className={cn(
                  "absolute left-0 w-6 h-6 rounded-full border-2 flex items-center justify-center",
                  index === 0 
                    ? "bg-primary border-primary" 
                    : "bg-card border-border"
                )}
              >
                <div 
                  className={cn(
                    "w-2 h-2 rounded-full",
                    index === 0 ? "bg-primary-foreground" : "bg-muted-foreground"
                  )} 
                />
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-sm text-foreground">
                    {entry.action}
                  </span>
                </div>
                
                {entry.details && (
                  <p className="text-sm text-muted-foreground mt-1">
                    {entry.details}
                  </p>
                )}
                
                <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <User className="h-3 w-3" />
                    {entry.performedBy}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {format(new Date(entry.performedAt), 'MMM d, yyyy HH:mm')}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
