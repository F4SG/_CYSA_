using Cysa.Web.Api.Dto;
using Cysa.Web.Api.Models;
using Cysa.Web.Api.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace Cysa.Web.Api.Controllers;

[ApiController,Authorize(Policy="Leer")]
[ProducesResponseType<ProblemDetails>(400),ProducesResponseType<ProblemDetails>(401),ProducesResponseType<ProblemDetails>(403)]
public abstract class ConsultaController<T,TEntrada,TSalida>(RecursoService<T,TEntrada,TSalida> service) : ControllerBase
    where T:Entidad,new() where TEntrada:IEntrada<T> where TSalida:ISalida<T,TSalida>
{
    protected readonly RecursoService<T,TEntrada,TSalida> Service=service;
    [HttpGet,ProducesResponseType(200)]
    public async Task<ActionResult<List<TSalida>>> Listar([FromQuery]int pagina=1,[FromQuery]int tamano=50,CancellationToken ct=default) => Ok(await Service.Listar(pagina,tamano,ct));
    [HttpGet("{id:int}"),ProducesResponseType(200),ProducesResponseType<ProblemDetails>(404)]
    public async Task<ActionResult<TSalida>> Obtener(int id,CancellationToken ct)
    {
        var result=await Service.Obtener(id,ct); return result is null ? NotFound(new ProblemDetails{Status=404,Title="Recurso inexistente."}) : Ok(result);
    }
}

public abstract class RegistroController<T,TEntrada,TSalida>(RecursoService<T,TEntrada,TSalida> service) : ConsultaController<T,TEntrada,TSalida>(service)
    where T:Entidad,new() where TEntrada:IEntrada<T> where TSalida:ISalida<T,TSalida>
{
    [HttpPost,Authorize(Policy="Escribir"),ProducesResponseType(201),ProducesResponseType<ProblemDetails>(409)]
    public async Task<ActionResult<TSalida>> Crear(TEntrada input,CancellationToken ct)
    {
        var result=await Service.Crear(input,ct);
        // El ID se obtiene del DTO de salida, generado por el servidor.
        var id=(int)typeof(TSalida).GetProperty("Id")!.GetValue(result)!;
        return CreatedAtAction(nameof(Obtener),new{id},result);
    }
}

public abstract class CrudController<T,TEntrada,TSalida>(RecursoService<T,TEntrada,TSalida> service) : RegistroController<T,TEntrada,TSalida>(service)
    where T:Entidad,new() where TEntrada:IEntrada<T> where TSalida:ISalida<T,TSalida>
{
    [HttpPut("{id:int}"),Authorize(Policy="Escribir"),ProducesResponseType(204),ProducesResponseType<ProblemDetails>(404),ProducesResponseType<ProblemDetails>(409)]
    public async Task<IActionResult> Actualizar(int id,TEntrada input,CancellationToken ct) => await Service.Actualizar(id,input,ct) ? NoContent() : NotFound();
    [HttpDelete("{id:int}"),Authorize(Policy="Escribir"),ProducesResponseType(204),ProducesResponseType<ProblemDetails>(404),ProducesResponseType<ProblemDetails>(409)]
    public async Task<IActionResult> Eliminar(int id,CancellationToken ct) => await Service.Eliminar(id,ct) ? NoContent() : NotFound();
}
