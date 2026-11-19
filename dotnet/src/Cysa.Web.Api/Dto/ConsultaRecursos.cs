using System.ComponentModel.DataAnnotations;

namespace Cysa.Web.Api.Dto;

public sealed class ConsultaRecursos
{
    [Range(1,10000)] public int Pagina { get; set; } = 1;
    [Range(1,200)] public int Tamano { get; set; } = 50;
    [StringLength(120)] public string? Buscar { get; set; }
    [Range(1,int.MaxValue)] public int? CorredorId { get; set; }
    [Range(1,int.MaxValue)] public int? InterseccionId { get; set; }
    [Range(1,int.MaxValue)] public int? AccesoId { get; set; }
    public bool? Activa { get; set; }
}
