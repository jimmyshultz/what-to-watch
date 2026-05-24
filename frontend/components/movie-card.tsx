"use client";

import Image from "next/image";
import { Film } from "lucide-react";

import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import type { MovieRecommendation } from "@/lib/types";

interface MovieCardProps {
  movie: MovieRecommendation;
}

export function MovieCard({ movie }: MovieCardProps) {
  const genres = movie.genres
    .split(",")
    .map((g) => g.trim())
    .filter(Boolean)
    .slice(0, 3);

  return (
    <Card className="overflow-hidden p-0">
      <div className="flex flex-col sm:flex-row">
        <div className="relative w-full sm:w-40 aspect-[2/3] shrink-0 bg-muted">
          {movie.poster_url ? (
            <Image
              src={movie.poster_url}
              alt={`Poster for ${movie.title}`}
              fill
              sizes="(max-width: 640px) 100vw, 160px"
              className="object-cover"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-muted-foreground">
              <Film className="h-10 w-10" aria-hidden />
            </div>
          )}
        </div>
        <div className="flex flex-1 flex-col gap-2 p-4">
          <div>
            <h3 className="text-lg font-semibold leading-tight">
              {movie.title}
              {movie.release_year > 0 && (
                <span className="font-normal text-muted-foreground">
                  {" "}
                  ({movie.release_year})
                </span>
              )}
            </h3>
            {movie.director && (
              <p className="text-sm text-muted-foreground">
                Directed by {movie.director}
              </p>
            )}
          </div>
          {genres.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {genres.map((g) => (
                <Badge key={g} variant="outline" className="font-normal">
                  {g}
                </Badge>
              ))}
            </div>
          )}
          {movie.explanation && (
            <p className="text-sm leading-relaxed pt-1">{movie.explanation}</p>
          )}
        </div>
      </div>
    </Card>
  );
}

export function MovieCardSkeleton() {
  return (
    <Card className="overflow-hidden p-0">
      <div className="flex flex-col sm:flex-row">
        <Skeleton className="w-full sm:w-40 aspect-[2/3] rounded-none" />
        <div className="flex-1 space-y-2 p-4">
          <Skeleton className="h-5 w-3/4" />
          <Skeleton className="h-4 w-1/3" />
          <div className="flex gap-1.5 pt-1">
            <Skeleton className="h-5 w-14" />
            <Skeleton className="h-5 w-14" />
          </div>
          <Skeleton className="h-4 w-full mt-2" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      </div>
    </Card>
  );
}
