using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Cysa.Web.Api.Data.Migrations
{
    /// <inheritdoc />
    public partial class AuditoriaDecisionesYModelosFuturos : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AlterColumn<DateTimeOffset>(
                name: "ActivadaUtc",
                table: "VersionModelo",
                type: "datetimeoffset",
                nullable: true,
                oldClrType: typeof(DateTimeOffset),
                oldType: "datetimeoffset");

            migrationBuilder.AddColumn<Guid>(
                name: "SolicitudId",
                table: "Bitacora",
                type: "uniqueidentifier",
                nullable: true);

            migrationBuilder.CreateIndex(
                name: "IX_Bitacora_SolicitudId",
                table: "Bitacora",
                column: "SolicitudId",
                unique: true,
                filter: "[SolicitudId] IS NOT NULL");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex(
                name: "IX_Bitacora_SolicitudId",
                table: "Bitacora");

            migrationBuilder.DropColumn(
                name: "SolicitudId",
                table: "Bitacora");

            migrationBuilder.AlterColumn<DateTimeOffset>(
                name: "ActivadaUtc",
                table: "VersionModelo",
                type: "datetimeoffset",
                nullable: false,
                defaultValue: new DateTimeOffset(new DateTime(1, 1, 1, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)),
                oldClrType: typeof(DateTimeOffset),
                oldType: "datetimeoffset",
                oldNullable: true);
        }
    }
}
